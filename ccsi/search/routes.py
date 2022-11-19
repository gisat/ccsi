from flask import Response, request, abort, render_template, make_response, Blueprint, redirect, url_for, jsonify
import flask.scaffold
flask.helpers._endpoint_from_view_func = flask.scaffold._endpoint_from_view_func
from flask_restful import Resource, Api
from ccsi.config import Config
from ccsi.resource.query import QueryResource
from ccsi.resource.output import ResourceXMLResponse, AllResourceXMLResponse, ResourceJsonResponse
import datetime
from ccsi.storage import storage


api_search = Blueprint('api_search', __name__)
api = Api(api_search)


# helpers function
def check_form(form):
    """check if is correct form of response formtat in url"""
    if form not in Config.RESPONSE_FORM:
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
        self.resource_schemas = kwargs['resource_schemas']
        self.translator = kwargs['translator']
        self.connection = kwargs['connection']
        self.parser = kwargs['parser']
        self.resource_description = kwargs['resource_description']

    def get(self, form):
        check_form(form)
        query_processor = QueryResource(self.resource_schemas, self.translator, self.connection, self.parser)

        try:
            query_processor.process_query(request.args)
        except Exception as error:
            return render_error(error)

        if len(query_processor.errors) > 0:
            return make_response(jsonify(query_processor.errors))

        if form == 'atom':
            response = AllResourceXMLResponse(Config.NAMESPACES, self.resource_description,
                                              query_processor, request.url_root)
            return Response(response.build_response(), mimetype='application/xml',
                            content_type='text/xml; charset=utf-8')
        if form == 'json':
            response = ResourceJsonResponse(query_processor)
            return jsonify(response.build_response())


api.add_resource(AllSearch, '/<string:form>/search',
                 resource_class_kwargs={'resource_schemas': storage.resource_schemas,
                                        'translator': storage.translator,
                                        'connection': storage.connection,
                                        'parser': storage.parser,
                                        'resource_description': storage.resource_description})


class AllSearchDescription(Resource):
    """Search endpoint returning number of occurrences across all registered resources"""
    def __init__(self, **kwargs):
        self.description = kwargs['descriptions']

    def get(self):
        url = f'{request.url_root}/search'
        return Response(self.description.build_description('ccsi', url),
                        mimetype='application/xml', content_type='text/xml; charset=utf-8')


api.add_resource(AllSearchDescription, '/<string:form>/search/description.xml',
                 resource_class_kwargs={'descriptions': storage.description})


# response endpoint
class ResourceSearch(Resource):
    """Search endpoint returning the occurrences from single registered resources"""

    def __init__(self, **kwargs):
        self.schema_builder = kwargs['schema_builder']
        self.resource_schemas = kwargs['resource_schemas']
        self.translator = kwargs['translator']
        self.connection = kwargs['connection']
        self.parser = kwargs['parser']
        self.response_spec = kwargs['response_spec']

    def get(self, resource_name, form):
        check_form(form)
        exist(resource_name)
        query_processor = QueryResource(self.resource_schemas, self.translator, self.connection, self.parser)


        try:
            query_processor.process_query(request.args, resource_name)
        except Exception as error:
            return render_error(error)

        if len(query_processor.errors) > 0:
            return make_response(jsonify({'message': query_processor.errors}), 500)

        if form == 'atom':
            url = f'{request.url_root}{resource_name}/{form}/search'
            response = ResourceXMLResponse(self.response_spec, Config.NAMESPACES, query_processor, url, resource_name)
            return Response(response.build_response(), mimetype='application/xml', content_type='text/xml; charset=utf-8')
        elif form == 'json':
            response = ResourceJsonResponse(query_processor)
            return jsonify(response.build_response())


api.add_resource(ResourceSearch, '/<string:resource_name>/<string:form>/search',
                 resource_class_kwargs={'schema_builder': storage.query_schema_builder,
                                        'resource_schemas': storage.resource_schemas,
                                        'translator': storage.translator,
                                        'connection': storage.connection,
                                        'parser': storage.parser,
                                        'response_spec': storage.response_specification})


class ResourceSearchDescription(Resource):
    """Search endpoint returning number of occurrences across all registered resources"""
    def __init__(self, **kwargs):
        self.description = kwargs['description']

    def get(self, resource_name):
        exist(resource_name)
        url = f'{request.url_root}{resource_name}/search'
        return Response(self.description.build_description(resource_name, url),
                        mimetype='application/xml', content_type='text/xml; charset=utf-8')


api.add_resource(ResourceSearchDescription, '/<string:resource_name>/search/description.xml',
                 resource_class_kwargs={'description': storage.description})


class ResourceProxy(Resource):
    """Proxy for management of onda resources"""
    def __init__(self, **kwargs):
        self.proxy = kwargs['proxy']

    def get(self, resource_name, identifier):
        exist(resource_name)
        return self.proxy(resource_name, identifier)

    def post(self, resource_name, identifier):
        exist(resource_name)
        return self.proxy(resource_name, identifier)


api.add_resource(ResourceProxy, '/<string:resource_name>/proxy/<string:identifier>',
                 resource_class_kwargs={'proxy': storage.get_container('proxy')})


@api_search.context_processor
def my_utility_processor():

    def date_now(format="%d.m.%Y %H:%M:%S"):
        """ returns the formated datetime """
        return datetime.datetime.now().strftime(format)

    return dict(date_now=date_now)



