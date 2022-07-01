from lxml.etree import Element, SubElement, tostring, register_namespace
from marshmallow import fields, post_load
from pydantic import BaseModel, Extra
from flask import request
from urllib.parse import urlencode

from ccsi.base import ExcludeSchema, Container
from ccsi.config import Config
from datetime import datetime
from ccsi.resource.schemas.json_ouput import Tag, Attrib


def build_link_tag(tag: str, href: str, rel: str,):
    attrib = Attrib(href=href, rel=rel)
    return Tag(tag=tag, attrib=attrib)


def build_self_tag(params: dict):
    return build_link_tag(tag='link', href=f'{request.base_url}?{urlencode(params)}', rel='self')


def build_first_tag(params: dict):
    params['startIndex'] = 0
    return build_link_tag(tag='link', href=f'{request.base_url}?{urlencode(params)}', rel='first')


def build_next_tag(params: dict, total_results: int):
    if (params['startIndex'] + params['maxRecords']) < total_results:
        params['startIndex'] = params['startIndex'] + params['maxRecords']
    return build_link_tag(tag='link', href=f'{request.base_url}?{urlencode(params)}', rel='next')


def build_last_tag(params: dict, total_results: int):
    startIndex = (total_results //params['maxRecords']) * params['maxRecords']
    params['startIndex'] = startIndex
    return build_link_tag(tag='link', href=f'{request.base_url}?{urlencode(params)}', rel='last')


class Description:

    def __init__(self, ns, resource_parameters):
        self.ns = ns
        self.resource_parameters = resource_parameters
        self.feed = None
        self.resource_name = ''
        self.url_root = ''

    def build_description(self, resource_name, url_root):
        self.resource_name = resource_name
        self.url_root = url_root
        self._create_head()
        self._create_body()
        return tostring(self.feed, pretty_print=True).decode("utf-8")

    def _create_head(self):
        uri = '{http://a9.com/-/spec/opensearch/1.1/}'
        self.feed = Element(f'{uri}OpenSearchDescription', nsmap=self._nsmap())
        self._create_SubElement(self.feed, f'{uri}ShortName', text=f'CCSI')
        self._create_SubElement(self.feed, f'{uri}LongName',
                                text=f'Copernicus Core Service Interface')
        self._create_SubElement(self.feed, f'{uri}Description',
                                text=f'OpenSearch description document that describes how to '
                                                               f'query data provided by {self.resource_name} endpoint')
        self._create_SubElement(self.feed, f'{uri}Contact',
                                text='michal.opletal@gisat.cz')
        attrib = {"type": self._format_from_url(), "rel": "results", "template": self._create_url_template()}
        self._create_SubElement(self.feed, f'{uri}Url', attrib=attrib)

    def _format_from_url(self):
        if self.url_root.__contains__('json'):
            return "application/json"
        elif self.url_root.__contains__('atom'):
            return "application/atom+xml"

    def _create_body(self):
        """method select parameters to describe and inject them into the funct that create respective xml element"""
        if self.resource_name == 'ccsi':
            for _, properties in self.resource_parameters.get_item('ccsi').get().items():
                element = DescriptionElementSchema().load(properties)
                self.feed.append(element)
        else:
            for parameter, properties in self.resource_parameters.get_item('ccsi').get().items():
                if parameter in self.resource_parameters.get_item(self.resource_name).get():
                    resource_parameter = self.resource_parameters.get_item(self.resource_name).get_parameter(parameter)
                    if parameter == 'resource' or parameter == 'collection':
                        param_property = self.resource_parameters.get_item(self.resource_name).get_parameter(parameter)
                        properties['values'] = param_property.definitions['mapping']
                    if hasattr(resource_parameter, 'mapping'):
                        properties['values'] = resource_parameter.mapping.keys()
                    element = DescriptionElementSchema().load(properties)
                    self.feed.append(element)

    def _create_url_template(self):
        """method select parameters to describe and inject them into the funct that create respective xml element"""
        query = {}
        if self.resource_name == 'ccsi':
            for parameter, properties in self.resource_parameters.get_item('ccsi').get().items():
                query.update({parameter: f'{{{properties["namespace"]}:{parameter}?}}'})

        else:
            for parameter, properties in self.resource_parameters.get_item('ccsi').get().items():
                if parameter in self.resource_parameters.get_item(self.resource_name).get():
                    query.update({parameter: f'{{{properties["namespace"]}:{parameter}?}}'})
        return self.url_root + '?' + self._encode(query)

    def _encode(self, query_params):
        return '&'.join([f'{key}={value}' for key, value in query_params.items()])

    @staticmethod
    def _create_SubElement(parent, tag, attrib={}, text=None, nsmap=None, **_extra):
        result = SubElement(parent, tag, attrib, nsmap, **_extra)
        result.text = text
        return result

    def _nsmap(self):
        nsmap = {}
        for name, ns in self.ns.items():
            for prefix, uri in ns.items():
                register_namespace(prefix, uri)
                nsmap.update({prefix: uri})

        return nsmap


class DescriptionElementSchema(ExcludeSchema):
    name = fields.String(required=True)
    title = fields.String(required=False)
    namespace = fields.String(required=True)
    values = fields.List(fields.String(), required=False, many=True)

    def create_element(self, tag, attrib={},  nsmap=None, **ignore):
        element = Element(tag, attrib, nsmap)
        return element

    @post_load()
    def make_element(self, data, **ignore):
        uri = '{http://a9.com/-/spec/opensearch/extensions/parameters/1.0/}'
        prefix = data.pop('namespace')
        name = data['name']
        data['value'] = f'{{{prefix}:{name}}}'
        if 'values' in data:
            values = data.pop('values')
            element = self.create_element(f'{uri}Parameter', attrib=data, nsmap=Config.NAMESPACES.get('param'))
            for value in values:
                sub_element = self.create_element(f'{uri}Option', attrib={'value': value},
                                                  nsmap=Config.NAMESPACES.get('param'))
                element.append(sub_element)
        else:
            element = self.create_element(f'{uri}Parameter', attrib=data, nsmap=Config.NAMESPACES.get('param'))
        return element


class ResponseSpecContainer(Container):

    def create(self, parameters):
        for parameter, properties in parameters.items():
            self.update(parameter, properties)


# schema

class ResourceXMLResponse:

    def __init__(self, response_spec, namespaces, query_processor, base_url, resource_name):
        self.response_spec = response_spec
        self.namespaces = namespaces
        self.resource_name = resource_name
        self.response = query_processor.feeds.get(resource_name)
        if query_processor.feeds.get(resource_name).totalResults:
            self.total_results = query_processor.feeds.get(resource_name).totalResults
        else:
            self.total_results = 0
        self.query = query_processor.valid_queries.get(resource_name)
        self.base_url = base_url

    def build_response(self):
        self._create_head()
        self._create_body()
        encoding = "utf-8"
        xml = tostring(self.feed, pretty_print=True, encoding="unicode")
        # xml = xml if xml.startswith('<?xml') else '<?xml version="1.0" encoding="%s"?>%s' % (encoding, xml)
        # return unescape(xml)
        return xml

    def _create_head(self):
        atom_uri = self.get_uri('atom')
        os_uri = self.get_uri('os')

        self.feed = Element(f'{{{atom_uri}}}Feed', nsmap=self._nsmap())
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Title', text=f'Copernicus Core Service Interface')
        author = self._create_SubElement(self.feed, f'{{{atom_uri}}}Author')
        self._create_SubElement(author, f'{{{atom_uri}}}Name', text=f'Gisat')
        self._create_SubElement(author, f'{{{atom_uri}}}email', text='michal.opletal@gisat.cz')
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Update', text=datetime.now().strftime("%m-%d-%Y, %H:%M:%S"))
        self._create_head_links()
        self._create_SubElement(self.feed, f'{{{os_uri}}}TotalResults', text=str(self.total_results))
        self._create_SubElement(self.feed, f'{{{os_uri}}}startIndex', text=str(self.query['startIndex']))
        self._create_SubElement(self.feed, f'{{{os_uri}}}itemsPerPage', text=str(self.query['maxRecords']))

    def _create_head_links(self):
        atom_uri = self.get_uri('atom')
        start_index = int(self.query['startIndex'])
        max_record = int(self.query['maxRecords'])
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Link',
                                attrib={"rel": "search", "href": f"{self.base_url}/description.xml"})
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Link',
                                attrib={"rel": "self", "href": f"{self.base_url}?{self._encode(self.query)}"})

        first_query = self.query.copy()
        first_query['startIndex'] = '0'
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Link',
                                attrib={"rel": "first", "href": f"{self.base_url}?{self._encode(first_query)}"})

        next_query = self.query.copy()
        if self.total_results - max_record > 0:
            next_query['startIndex'] = str(start_index + max_record)
            self._create_SubElement(self.feed, f'{{{atom_uri}}}Link',
                                    attrib={"rel": "next", "href": f"{self.base_url}?{self._encode(next_query)}"})

        last_query = self.query.copy()
        if self.total_results - max_record >= 0:
            last_query['startIndex'] = str(self.total_results - max_record)
            self._create_SubElement(self.feed, f'{{{atom_uri}}}Link',
                                    attrib={"rel": "last", "href": f"{self.base_url}?{self._encode(last_query)}"})

    def _create_body(self):
        for entry in self.response.entries:
            self.feed.append(entry.xml())

    @staticmethod
    def _create_SubElement(parent, tag, attrib={}, text=None, nsmap=None, **_extra):
        result = SubElement(parent, tag, attrib, nsmap, **_extra)
        result.text = text
        return result

    def _nsmap(self):
        nsmap = {}
        for name, ns in self.namespaces.items():
            for prefix, uri in ns.items():
                register_namespace(prefix, uri)
                nsmap.update({prefix: uri})
        return nsmap

    def get_uri(self, prefix):
        return self.namespaces.get(prefix).get(prefix)

    def _encode(self, query_params):
        return '&'.join([f'{key}={value}' for key, value in query_params.items()])


class AllResourceXMLResponse:

    def __init__(self, namespaces, resource_description, query_processor, base_url):
        self.namespaces = namespaces
        self.resource_description = resource_description
        self.total_results = {resource_name: feed.totalResults for resource_name, feed in query_processor.feeds.items()}
        self.resource_query = query_processor.valid_queries
        self.query = query_processor.valid_query
        self.base_url = base_url

    def build_response(self):
        self._create_head()
        self._create_body()
        encoding = "utf-8"
        xml = tostring(self.feed, pretty_print=True, encoding="unicode")
        return xml

    def _create_head(self):
        atom_uri = self.get_uri('atom')
        os_uri = self.get_uri('os')

        self.feed = Element(f'{{{atom_uri}}}Feed', nsmap=self._nsmap())
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Title', text=f'Copernicus Core Service Interface')
        author = self._create_SubElement(self.feed, f'{{{atom_uri}}}Author')
        self._create_SubElement(author, f'{{{atom_uri}}}Name', text=f'Gisat')
        self._create_SubElement(author, f'{{{atom_uri}}}email', text='michal.opletal@gisat.cz')
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Update', text=datetime.now().strftime("%m-%d-%Y, %H:%M:%S"))
        self._create_head_links()

        all_results = sum(self.total_results.values())
        self._create_SubElement(self.feed, f'{{{os_uri}}}TotalResults', text=str(all_results))

    def _create_head_links(self):
        atom_uri = self.get_uri('atom')
        start_index = int(self.query['startIndex'])
        max_record = int(self.query['maxRecords'])
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Link',
                                attrib={"rel": "search", "href": f"{self.base_url}/search/description.xml"})
        self._create_SubElement(self.feed, f'{{{atom_uri}}}Link',
                                attrib={"rel": "self", "href": f"{self.base_url}/atom/search?"
                                                               f"{self._encode(self.query)}"})

    def _create_body(self):
        atom_uri = self.get_uri('atom')
        os_uri = self.get_uri('os')
        ccsi_uri = self.get_uri('ccsi')

        for resource_name, total_results in self.total_results.items():
            entry_tag = Element(f'{{{atom_uri}}}Entry')
            short_name = self.resource_description.get_item(resource_name).get('short_name')
            self._create_SubElement(entry_tag, f'{{{ccsi_uri}}}Resource', text=short_name)
            self._create_SubElement(entry_tag, f'{{{os_uri}}}TotalResults', text=str(total_results))
            self._create_SubElement(entry_tag, f'{{{atom_uri}}}Link',
                                    attrib={"rel": "search", "href": f"{self.base_url}/{resource_name}/atom/search?"
                                                                     f"{self._encode(self.resource_query.get(resource_name))}"})
            self.feed.append(entry_tag)

    @staticmethod
    def _create_SubElement(parent, tag, attrib={}, text=None, nsmap=None, **_extra):
        result = SubElement(parent, tag, attrib, nsmap, **_extra)
        result.text = text
        return result

    def _nsmap(self):
        nsmap = {}
        for name, ns in self.namespaces.items():
            for prefix, uri in ns.items():
                register_namespace(prefix, uri)
                nsmap.update({prefix: uri})
        return nsmap

    def get_uri(self, prefix):
        return self.namespaces.get(prefix).get(prefix)

    def _encode(self, query_params):
        return '&'.join([f'{key}={value}' for key, value in query_params.items()])


class ResourceDescriptionSchema(ExcludeSchema):
    name = fields.String()


class ResourceDescriptionContainer(Container):

    def create(self, resource_name, description):
        self.update(resource_name, description)


class ResourceJsonResponse:

    def __init__(self, query_processor):
        self.query_processor = query_processor

    def build_response(self):
        feeds = []
        for _, feed in self.query_processor.feeds.items():
            feed.head.append(build_self_tag(self.query_processor.valid_query))
            feed.head.append(build_first_tag(self.query_processor.valid_query))
            feed.head.append(build_next_tag(self.query_processor.valid_query, feed.totalResults))
            feed.head.append(build_last_tag(self.query_processor.valid_query, feed.totalResults))

            feeds.append(feed.dict())


        return feeds


