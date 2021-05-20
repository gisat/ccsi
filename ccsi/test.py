from ccsi import init_app
from ccsi.storage import storage
from ccsi.resource.query import QueryResource
from ccsi.resource.output import AllResourceXMLResponse
from ccsi.config import Config

def render_error(error):
    msg, status_code = storage.errors.process_error(error)
    # template = render_template('errors/error.xml', msg=msg)
    # response = make_response(template)
    response.headers['Content-Type'] = 'application/xml'
    return response


class AllSearch:
    """Search endpoint returning number of occurrences across all registered resources"""

    def __init__(self, **kwargs):
        self.resources_schemas = storage.resource_schemas
        self.translator = storage.translator
        self.connections = storage.connections
        self.parsers = storage.parsers
        self.resource_description = storage.resource_description


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



class FakeRequest:

    def __init__(self, query):
        self.args=query
        self.url_root = 'foo.bar/atom'


if __name__ == '__main__':
    init_app()
    query = {'orbitNumber': '106',
             'timeStart': '2017-10-10',
             'processingLevel': 'L2A'}

    request = FakeRequest(query)
    search = AllSearch()
    search.get('atom', request)

