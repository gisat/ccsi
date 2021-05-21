from flask import Response, request, abort, render_template, make_response, Blueprint, redirect, url_for
from flask_restful import Resource, Api
from ccsi.config import Config
from ccsi.storage import storage
from ccsi.resource.query import QueryResource
from ccsi.resource.parser import FeedSchema
from ccsi.resource.output import ResourceXMLResponse, ResponseXMLTagSchema, AllResourceXMLResponse
import datetime

api_search = Blueprint('api_search', __name__)
api = Api(api_search)


# helpers function
def check_form(form):
    """check if is correct form of response formtat in url"""
    if form not in Config.response_form:
        abort(400, 'Invalid response format in url')


def exist(resource_name):
    if resource_name in storage.resources_parameters.get_item_list()['items']:
        return True
    else:
        abort(400, f'Unknown resource name {resource_name}')

def render_error(error):
    msg, status_code = storage.errors.process_error(error)
    template = render_template('errors/error.xml', msg=msg)
    response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


# main endpoint
class AllSearch(Resource):
    """Search endpoint returning number of occurrences across all registered resources"""

    def __init__(self, **kwargs):
        self.resources_schemas = kwargs['resources_schemas']
        self.translator = kwargs['translator']
        self.connections = kwargs['connections']
        self.parsers = kwargs['parsers']
        self.resource_description = kwargs['resource_description']

    def get(self, form):
        check_form(form)
        query_processor = QueryResource(self.resources_schemas, self.translator, self.connections, self.parsers)

        try:
            query_processor.process_query(request.args)
        except Exception as error:
            return render_error(error)

        if form == 'atom':
            response = AllResourceXMLResponse(Config.namespaces, self.resource_description,
                                              query_processor, request.url_root)
            return Response(response.build_response(), mimetype='application/xml',
                            content_type='text/xml; charset=utf-8')
        if form == 'json':
            return abort(400, 'Json format temporary disabled')


api.add_resource(AllSearch, '/<string:form>/search',
                 resource_class_kwargs={'resources_schemas': storage.resource_schemas,
                                        'translator': storage.translator,
                                        'connections': storage.connections,
                                        'parsers': storage.parsers,
                                        'resource_description': storage.resource_description})


class AllSearchDescription(Resource):
    """Search endpoint returning number of occurrences across all registered resources"""
    def __init__(self, **kwargs):
        self.description = kwargs['descriptions']

    def get(self, form):
        check_form(form)
        url = f'{request.url_root}{form}/search'
        return Response(self.description.build_description('ccsi', url),
                        mimetype='application/xml', content_type='text/xml; charset=utf-8')


api.add_resource(AllSearchDescription, '/<string:form>/search/description.xml',
                 resource_class_kwargs={'descriptions': storage.description})


# response endpoint
class ResourceSearch(Resource):
    """Search endpoint returning the occurrences from single registered resources"""

    def __init__(self, **kwargs):
        self.schema_builder = kwargs['schema_builder']
        self.resources_schemas= kwargs['resources_schemas']
        self.translator = kwargs['translator']
        self.connections = kwargs['connections']
        self.parsers = kwargs['parsers']
        self.response_spec = kwargs['response_spec']

    def get(self, resource_name, form):
        check_form(form)
        exist(resource_name)
        query_processor = QueryResource(self.resources_schemas, self.translator, self.connections, self.parsers)

        if form == 'atom':
            try:
                query_processor.process_query(request.args, resource_name)
            except Exception as error:
                return render_error(error)
            url = f'{request.url_root}{resource_name}/{form}/search'
            response = ResourceXMLResponse(FeedSchema, ResponseXMLTagSchema, self.response_spec,
                                           Config.namespaces, query_processor, url, resource_name)
            return Response(response.build_response(), mimetype='application/xml', content_type='text/xml; charset=utf-8')

        elif form == 'json':
            return abort(400, 'Json format temporary disabled')

api.add_resource(ResourceSearch, '/<string:resource_name>/<string:form>/search',
                 resource_class_kwargs={'schema_builder': storage.query_schema_builder,
                                        'resources_schemas': storage.resource_schemas,
                                        'translator': storage.translator,
                                        'connections': storage.connections,
                                        'parsers': storage.parsers,
                                        'response_spec': storage.response_specification})


class ResourceSearchDescription(Resource):
    """Search endpoint returning number of occurrences across all registered resources"""
    def __init__(self, **kwargs):
        self.description = kwargs['description']

    def get(self, resource_name, form):
        check_form(form)
        exist(resource_name)
        url = f'{request.url_root}{resource_name}/{form}/search'
        return Response(self.description.build_description(resource_name, url),
                        mimetype='application/xml', content_type='text/xml; charset=utf-8')


api.add_resource(ResourceSearchDescription, '/<string:resource_name>/<string:form>/search/description.xml',
                 resource_class_kwargs={'description': storage.description})


@api_search.context_processor
def my_utility_processor():

    def date_now(format="%d.m.%Y %H:%M:%S"):
        """ returns the formated datetime """
        return datetime.datetime.now().strftime(format)

    return dict(date_now=date_now)



