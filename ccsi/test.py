from ccsi import init_app
from ccsi.storage import storage
from ccsi.resource.query import QueryResource
from ccsi.resource.output import AllResourceXMLResponse, ResourceXMLResponse, ResponseXMLTagSchema
from ccsi.config import Config
from ccsi.resource.parser import FeedSchema

def render_error(error):
    msg, status_code = storage.errors.process_error(error)
    # template = render_template('errors/error.xml', msg=msg)
    # response = make_response(template)
    # response.headers['Content-Type'] = 'application/xml'
    # return response


class AllSearch:
    """Search endpoint returning number of occurrences across all registered resources"""

    def __init__(self, **kwargs):
        self.resources_schemas = storage.resource_schemas
        self.translator = storage.translator
        self.connections = storage.connections
        self.parsers = storage.parsers
        self.resource_description = storage.resource_description
        self.response_spec = storage.response_specification


    def get(self, form, request):

        query_processor = QueryResource(self.resources_schemas, self.translator, self.connections, self.parsers)

        try:
            query_processor.process_query(request.args)
        except Exception as error:
            return render_error(error)

        if form == 'atom':
            response = AllResourceXMLResponse(Config.namespaces, self.resource_description,
                                              query_processor, request.url_root)
            return response.build_response()

    def get_resource(self, resource_name, form, request):
        query_processor = QueryResource(self.resources_schemas, self.translator, self.connections, self.parsers)

        if form == 'atom':
            try:
                query_processor.process_query(request.args, resource_name)
            except Exception as error:
                return render_error(error)
            url = f'{request.url_root}{resource_name}/{form}/search'
            response = ResourceXMLResponse(FeedSchema, ResponseXMLTagSchema, self.response_spec,
                                           Config.namespaces, query_processor, url, resource_name)
            return response.build_response()

class FakeRequest:

    def __init__(self, query):
        self.args=query
        self.url_root = 'foo.bar/atom'


if __name__ == '__main__':
    init_app()
    query = {
             'timeStart': '2017-10-10',
             'resource': 'creodias',
            'cloudCover': '0,10'}

    request = FakeRequest(query)
    search = AllSearch()
    # search.get('atom', request)
    search.get_resource('creodias_s1', 'atom', request)

