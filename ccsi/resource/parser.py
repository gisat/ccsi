from xml.sax.handler import ContentHandler, feature_namespaces
from xml.sax import make_parser
from lxml import etree
from io import StringIO, BytesIO
from marshmallow import fields, post_load
from marshmallow.validate import OneOf
from ccsi.base import Container, ExcludeSchema
from abc import ABC, abstractmethod
import ast


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
        self.text = ''
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

    def find_tag(self, tag_type: str, tag_name: str):
        for tag in self.entry:
            if tag.__getattribute__(tag_type) == tag_name:
                return tag
        return None

    def delete_tag_by_id(self, _id):
        self.entry = [tag for tag in self.entry if not id(tag) == _id]




class EntrySchema(ExcludeSchema):
    entry = fields.Nested(TagSchema, many=True)


class Feed:

    def __init__(self):
        self.entries = []
        self.head = []
        self.totalResults = 0

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
class Parser(ABC):

    @abstractmethod
    def parse(self, content) -> Feed:
        pass


class XMLSaxHandler(ContentHandler, Parser):
    
    def __init__(self, parameters, feed: Feed, entry: Entry, preprocessor=None, **ignore):
        super(XMLSaxHandler, self).__init__()
        self.parameters = parameters
        self._preprocessor = preprocessor
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
       for value in self.current_tag.source['attrib']:
           if value in [name[1] for name in attrs.keys()]:
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
             self.current_tag.text += content

    def parse(self, content):
        self.feed = self._feed()
        parser = make_parser()
        parser.setContentHandler(self)
        parser.setFeature(feature_namespaces, 1)
        stream = self.stream(content)
        parser.parse(stream)
        return self.feed

    def stream(self, source):
        if isinstance(source, bytes):
            return BytesIO(source)
        elif isinstance(source, str):
            return StringIO(source)


class XMLSaxHandlerCreo(XMLSaxHandler, Parser):

    def parse(self, content):
        self.feed = self._feed()
        parser = make_parser()
        parser.setContentHandler(self)
        parser.setFeature(feature_namespaces, 1)
        content = self.remove_resto(content)
        stream = self.stream(content)
        parser.parse(stream)
        return self.feed

    def remove_resto(self, source):
        parser = etree.XMLParser(recover=True)
        tree = etree.fromstring(source, parser)
        resto = tree.findall('{http://a9.com/-/spec/opensearch/1.1/}Query')
        for item in resto:
            item.getparent().remove(item)
        return etree.tostring(tree)


class WekeoParser(Parser):

    def __init__(self, parameters, feed: Feed, entry: Entry, preprocessor=None, **ignore):
        self.parameters = parameters
        self._preprocessor = preprocessor
        self._feed = feed
        self._entry = entry
        self.feed = None
        self.entry = None

    def parse(self, content):
        self.feed = self._feed()
        self._parse_head(content)
        self._parse_entries(content['content'])
        return self.feed

    def _parse_head(self, response):
        for parameter_name in self.parameters:
            tag = Tag(parameter_name, **self.parameters[parameter_name])
            if tag.location == 'head':
                tag.text = response[parameter_name]
                self.feed.add_to_head(tag)

    def _parse_entries(self, contents):
        for content in contents:
            content = self._preprocessor(content)
            entry = self._entry()
            for parameter_name in self.parameters:
                tag = Tag(parameter_name, **self.parameters[parameter_name])
                if tag.location == 'entry':
                    tag.text = content[parameter_name]
                    entry.add_tag(tag)
            self.feed.add_entry(entry)


def prodInfo2content(content):
    for k, v in content['productInfo'].items():
        content.update({k: v})
    return content


class CDSAPIParser(Parser):

    def __init__(self, parameters, feed: Feed, entry: Entry, preprocessor=None, **ignore):
        self.parameters = parameters
        self._preprocessor = preprocessor
        self._feed = feed
        self._entry = entry
        self.feed = None
        self.entry = None

    def parse(self, content):
        self.feed = self._feed()

        for parameter_name in self.parameters:
            tag = Tag(parameter_name, **self.parameters[parameter_name])
            if tag.location == 'head':
                tag.text = 1
                self.feed.add_to_head(tag)
            else:
                entry = self._entry()
                tag.text = content
                entry.add_tag(tag)
                self.feed.add_entry(entry)
        return self.feed


class OndaParser(Parser):

    def __init__(self, parameters, feed: Feed, entry: Entry, preprocessor=None, **ignore):
        self.parameters = parameters
        self._preprocessor = preprocessor
        self._feed = feed
        self._entry = entry
        self.feed = None
        self.entry = None

    def parse(self, content):
        self.feed = self._feed()

        for record in content.get('value'):
            entry = self._entry()
            for parameter_name in self.parameters:
                tag = Tag(parameter_name, **self.parameters[parameter_name])
                tag.text = record.get(parameter_name)
                entry.add_tag(tag)

            if entry.find_tag(tag_type='source_tag', tag_name='offline').text is True:
                entry.find_tag(tag_type='source_tag', tag_name='id').tag_spec = 'onda_id_to_esn'

            self.feed.add_entry(entry)
            self.feed.totalResults += 1
        return self.feed


PARSER_TYPES = {'xmlsax': XMLSaxHandler,
                'xmlsax_creo': XMLSaxHandlerCreo,
                'wekeo': WekeoParser,
                'cdsapi': CDSAPIParser,
                'onda': OndaParser}

PREPRCESSORS = {'prodInfo2content': prodInfo2content}


class ParserSchema(ExcludeSchema):
    typ = fields.String(required=True, validate=OneOf(PARSER_TYPES), allow_none=True)
    parameters = fields.Dict(required=False)
    preprocessor = fields.String(required=False)

    @post_load()
    def make_parser(self, data, **ignore):
        if data['typ']:
            data['feed'] = Feed
            data['entry'] = Entry
            data['preprocessor'] = PREPRCESSORS.get(data.get('preprocessor'))
            parser = PARSER_TYPES.get(data['typ'])
            return parser(**data)
        else:
            return None