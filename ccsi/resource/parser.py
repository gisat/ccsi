from xml.sax.handler import ContentHandler, feature_namespaces
from xml.sax import make_parser
from io import StringIO, BytesIO
from marshmallow import fields, post_load
from marshmallow.validate import OneOf


from ccsi.base import Container, ExcludeSchema


class Tag:

    def __init__(self, source_tag, tag, tag_spec=None, source=None, uri=None,
                 mapping=None, location='entry'):
        """

        :param source_tag: name o tag at original source
        :param tag: name of the mapped tag
        :param tag_spec: additional mapped tag specification
        :param source: where find the data, in text or attributes
        :param uri: namespace uri
        :param locations: 'entry' or none, if entry only tags in entry are considered
        """
        self.source_tag = source_tag
        self.tag = tag
        self.tag_spec = tag_spec
        self.uri = uri
        self.mapping = mapping
        self.source = source
        self.attrib = {}
        self.text = None
        self.location = location


class TagSchema(ExcludeSchema):
    tag = fields.String(required=True)
    tag_spec = fields.String(allow_none=True)
    text = fields.String(allow_none=True)
    attrib = fields.Dict(allow_none=True)
    uri = fields.String(allow_none=True)


class Entry:
    def __init__(self):
        self.entry = []

    def add_tag(self, tag: Tag):
        self.entry.append(tag)


class EntrySchema(ExcludeSchema):
    entry = fields.Nested(TagSchema, many=True)


class Feed:

    def __init__(self):
        self.entries = []
        self.head = []
        self.totalResults = None

    def add_entry(self, entry: Entry):
        self.entries.append(entry)

    def add_to_head(self, tag):
        # get total results easy accessible
        if tag.tag == 'totalResults':
            self.totalResults = int(tag.text)
        self.head.append(tag)


class FeedSchema(ExcludeSchema):
    head = fields.Nested(TagSchema, many=True)
    entries = fields.Nested(EntrySchema, many=True)


# SAX parser
class XMLSaxHandler(ContentHandler):
    
    def __init__(self, parameters, feed: Feed, entry: Entry, **ignore):
        super(XMLSaxHandler, self).__init__()
        self.parameters = parameters
        self._feed = feed
        self._entry = entry
        self.current_tag_name = None
        self.current_tag = None
        self.current_entry = None
        self.location = None
        self.feed = None
        self.entry = None

    def startElementNS(self, name, qname, attrs):
        uri, localname = name

        # get into entry tag
        if localname == 'entry':
            self.location = 'entry'
            self.current_entry = self._entry()

        if localname in self.parameters:
            tag = Tag(localname, **self.parameters[localname])
            if uri == tag.uri:
                self.current_tag_name = localname
                self.current_tag = tag
                if 'attrib' in self.current_tag.source:
                    self.set_entry_tag_attrib(attrs)

    def set_entry_tag_attrib(self, attrs):
        if [name[1] for name in attrs.keys()] == self.current_tag.source['attrib']:
           for value in self.current_tag.source['attrib']:
               self.current_tag.attrib.update({value: attrs.getValueByQName(value)})


    def endElementNS(self, name, qname):
        uri, localname = name

        if self.current_tag:
            if all([self.current_tag.source_tag == localname, self.current_tag.uri == uri]):
                if self.location == 'entry' and self.current_tag.location == 'entry':
                    self.current_entry.add_tag(self.current_tag)
                    self.current_tag = None
                    self.current_tag_name = None
                elif self.location != 'entry' and self.current_tag.location != 'entry':
                    self.feed.add_to_head(self.current_tag)
                    self.current_tag = None
                    self.current_tag_name = None
                else:
                    pass

        if localname == 'entry':
            self.location = None
            self.feed.add_entry(self.current_entry)
            self.current_entry = self._entry()

    def characters(self, content):
        if self.current_tag and self.current_tag_name == self.current_tag.source_tag:
         if self.current_tag.source == 'text':
             self.current_tag.text = content

    def parse(self, source):
        self.feed = self._feed()
        parser = make_parser()
        parser.setContentHandler(self)
        parser.setFeature(feature_namespaces, 1)
        stream = self.stream(source)
        parser.parse(stream)
        return self.feed

    def stream(self, source):
        if isinstance(source, bytes):
            return BytesIO(source)
        elif isinstance(source, str):
            return StringIO(source)


PARSER_TYPES = {'xmlsax': XMLSaxHandler}


class ParserSchema(ExcludeSchema):
    typ = fields.String(required=True, validate=OneOf(PARSER_TYPES), allow_none=True)
    parameters = fields.Dict(required=False)

    @post_load()
    def make_parser(self, data, **ignore):
        if data['typ']:
            data['feed'] = Feed
            data['entry'] = Entry
            parser = PARSER_TYPES.get(data['typ'])
            return parser(**data)
        else:
            return None


class ParserContainer(Container):

    def __init__(self, parser_schema):
        super(ParserContainer, self).__init__()
        self.parser_schema = parser_schema

    def create(self, resource_name, parameters):
        self.update(resource_name, self.parser_schema.load(parameters))
