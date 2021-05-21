class QueryResource:
    """class responsible for preparing the query request. Takes query parameters from ccsi api to resource api
    by selection of the resource"""

    def __init__(self, resources_schemas, translator, connections, parser):
        self.resources_schemas = resources_schemas
        self.translator = translator
        self.connection = connections
        self.parser = parser
        self.org_query = None
        self.valid_query = None
        self.valid_queries = {}
        self.translated_queries = {}
        self.responses = {}
        self.errors = {}
        self.feeds = {}

    def process_query(self, query, resource_name=None):
        """main class"""
        self._select_resources(query, resource_name)
        self._translate()
        self._request()
        self._parse()

    def _lower_values(self, query):
        return {key: value.lower() if isinstance(value, str) else value for key, value in query.items()}

    def _validate_resource(self, resource_name, schema, query):
        tested_query = schema.load(query)
        try:
            self.translator.translate(resource_name, tested_query)
            self.valid_queries.update({resource_name: schema.dump(tested_query)})
        except Exception:
            pass
        finally:
            pass

    def _select_resources(self, raw_query, resource_name=None):
        """select resource by query parameters"""

        self.org_query = raw_query
        lower = self._lower_values(raw_query)
        try:
            self.valid_query = self.resources_schemas.get_item('ccsi').load(lower)
        finally:
            pass

        if not resource_name:
            for resource_name, schema in self.resources_schemas.items.items():
                if resource_name != 'ccsi':
                    self._validate_resource(resource_name, schema, self.valid_query)
        else:
            self._validate_resource(resource_name, self.resources_schemas.get_item(resource_name), self.valid_query)

    def _translate(self):
        """translate from ccsi into resource api"""
        if self.valid_queries:
            for resource_name, query in self.valid_queries.items():
                self.translated_queries.update({resource_name: self.translator.translate(resource_name, query)})

    def _request(self):
        for resource_name, query in self.translated_queries.items():
            status_code, response = self.connection.get_item(resource_name).send_request(query)
            if status_code == 200:
                self.responses.update({resource_name: response.content})
            else:
                self.errors.update({resource_name: response.content})

    def _parse(self):
        for resource_name, response in self.responses.items():
            self.feeds.update({resource_name: self.parser.get_item(resource_name).parse(response)})
