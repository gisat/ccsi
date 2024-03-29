from pathlib import Path
from xml.sax.handler import ContentHandler, feature_namespaces
from xml.sax import make_parser
from lxml.etree import Element
from flask import request, url_for
from lxml import etree
from io import StringIO, BytesIO
from marshmallow import fields, post_load
from marshmallow.validate import OneOf
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, root_validator, Extra
from typing import Optional, List, Any

from ccsi.storage import storage
from ccsi import Config
from ccsi.base import ExcludeSchema


# tag_spec_func
def text2enclousure(text, **ignore):
    return None, {"rel": "enclosure", "type": "application/unknown", "href": text}


def find_in_dict(text, **ignore):
    return None


def text_to_path(text, **ignore):
    return None, {"rel": "path", "type": "application/unknown", "href": text}


def creodias_media_to_path(attrib, **ignore):
    text = attrib['url']
    text = text.lstrip('https://finder.creodias.eu/files')
    n_strip = text.find('.SAFE') + 5
    text = text[:n_strip]
    return None, {"rel": "path", "type": "application/unknown", "href": text}


def onda_id_to_enclousure(text, **ignore):
    enclouser = f'https://catalogue.onda-dias.eu/dias-catalogue/Products({text})/$value'
    return None, {"rel": "enclosure", "type": "application/unknown", "href": enclouser}


def onda_id_to_esn(text, **ignore):
    enclouser = f'https://catalogue.onda-dias.eu/dias-catalogue/Products({text})/Ens.Order'
    return None, {"rel": "enclosure", "type": "application/unknown", "href": enclouser}


def onda_id_to_esn_proxy(text, **ignore):
    enclouser  = f"{request.host_url}{url_for('api_search.resourceproxy', resource_name='onda_s3', identifier=text)}"
    return None, {"rel": "enclosure", "type": "application/unknown", "href": f'{enclouser}'}


def title_from_link(text, **ignore):
    return Path(text).name, None



TAG_SPEC_FUC = {'text_to_enclousure': text2enclousure,
                'text_to_path': text_to_path,
                'find_in_dict': find_in_dict,
                'creodias_media_to_path': creodias_media_to_path,
                'onda_id_to_enclosuer': onda_id_to_enclousure,
                'onda_id_to_esn': onda_id_to_esn,
                'onda_id_to_esn_proxy': onda_id_to_esn_proxy,
                'title_from_link': title_from_link}


# class Attrib(BaseModel):
#     rel: Optional[str] = Field(default='')
#     href: Optional[str] = Field(default='')


class Tag(BaseModel):
    """
    :param source_tag: name o tag at original source
    :param tag: name of the mapped tag
    :param tag_spec: additional mapped tag specification
    :param source: where find the data, in text or attributes
    :param uri: namespace uri
    :param locations: 'entry' or none, if entry only tags in entry are considered
    """
    tag: Optional[str]
    text: Optional[str] = Field(default='')
    attrib: dict = Field(default={'rel': '', 'href': ''})
    source_tag: str = Field(exclude=True)
    tag_spec: Optional[str] = Field(exclude=True)
    mapping: Optional[str] = Field(exclude=True)
    source: Optional[str] = Field(exclude=True)
    location: str = Field(default='entry', exclude=True)

    @root_validator(pre=True)
    def set_tag_content(cls, values):
        tag,  text, attrib, tag_spec = values.get('tag'), values.get('text'), values.get('attrib'),\
                                       values.get('tag_spec')
        content = storage.response_specification.get_item(tag)['content']

        if tag_spec:
            text, attrib = TAG_SPEC_FUC.get(tag_spec)(text=text, attrib=attrib)

        if content == 'text':
            values['text'], values['attrib'] = text, {}
        elif content == 'attrib':
            values['text'], values['attrib'] = '', attrib
        return values

    @property
    def nsmap(self):
        return Config.NAMESPACES.get(self.namespace)

    @property
    def uri(self):
        return self.nsmap.get(self.namespace)

    @property
    def namespace(self):
        return storage.response_specification.get_item(self.tag)['namespace']

    def xml(self) -> Element:
        """return xml representation of tag"""
        element = Element(f'{{{self.uri}}}{self.tag}', attrib=self.attrib, nsmap=self.nsmap)
        element.text = str(self.text)
        return element

    class Config:
        extra = Extra.ignore


class Entry(BaseModel):
    tag: str = Field(default='Entry')
    entry: List[Tag] = Field(default_factory=list)
    namespace: str = Field(default='atom', exclude=True)

    def add_tag(self, tag: Tag):
        self.entry.append(tag)

    def find_tag(self, tag_type: str, tag_name: str):
        for tag in self.entry:
            if tag.__getattribute__(tag_type) == tag_name:
                return tag
        return None

    def delete_tag_by_id(self, _id):
        self.entry = [tag for tag in self.entry if not id(tag) == _id]

    @property
    def nsmap(self):
        return Config.NAMESPACES.get(self.namespace)

    @property
    def uri(self):
        return self.nsmap.get(self.namespace)

    def xml(self) -> Element:
        entry = Element(f'{{{self.uri}}}{self.tag}')
        for tag in self.entry:
            entry.append(tag.xml())
        return entry


class Feed(BaseModel):
    entries: List[Entry] = Field(default_factory=list)
    head: List[Tag] = Field(default_factory=list)
    totalResults: int = Field(default=0)

    def add_entry(self, entry: Entry):
        self.entries.append(entry)

    def add_to_head(self, tag):
        # get total results easy accessible
        if tag.tag == 'totalResults':
            self.totalResults = int(tag.text)
        self.head.append(tag)


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
            tag = Tag(tag=localname, **self.parameters[localname])
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
            try:
                tag = Tag(source_tag=parameter_name, text=response[parameter_name], **self.parameters[parameter_name])
                if tag.location == 'head':
                    self.feed.add_to_head(tag)
            except KeyError:
                pass


    def _parse_entries(self, contents):
        for content in contents:
            content = self._preprocessor(content)
            entry = self._entry()
            for parameter_name in self.parameters:
                try:
                    tag = Tag(source_tag=parameter_name, text=content[parameter_name], **self.parameters[parameter_name])
                    if tag.location == 'entry':
                        entry.add_tag(tag)
                except KeyError:
                    pass
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
        entry = self._entry()
        self.feed.add_entry(entry)

        for parameter_name in self.parameters:
            tag = Tag(source_tag=parameter_name, text=content, **self.parameters[parameter_name])
            if tag.location == 'head':
                tag.text = 1
                self.feed.add_to_head(tag)
            else:
                entry.add_tag(tag)
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
                tag = Tag(source_tag=parameter_name, text=record.get(parameter_name), **self.parameters[parameter_name])
                entry.add_tag(tag)

            self.feed.add_entry(entry)
            self.feed.totalResults = content.get('totalResults')
        return self.feed


class OndaProxyParser(Parser):

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
                tag = Tag(source_tag=parameter_name, text=record.get(parameter_name), **self.parameters[parameter_name])
                entry.add_tag(tag)

            self.feed.add_entry(entry)
            self.feed.totalResults = content.get('totalResults')
        return self.feed


PARSER_TYPES = {'xmlsax': XMLSaxHandler,
                'xmlsax_creo': XMLSaxHandlerCreo,
                'wekeo': WekeoParser,
                'cdsapi': CDSAPIParser,
                'onda': OndaParser,
                'onda_proxy': OndaProxyParser}

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