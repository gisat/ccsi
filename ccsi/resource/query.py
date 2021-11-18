class QueryResource:
    """class responsible for preparing the query request. Takes query parameters from ccsi api to resource api
    by selection of the resource"""

    def __init__(self, resources_schemas, translator, connections, parser) -> object:
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
        self._prepare_valid_query(query)
        if not resource_name:
            self._select_resources()
        else:
            self._validate_resource(resource_name, self.resources_schemas.get_item(resource_name), self.valid_query)
        self._translate()
        self._request()
        self._parse()

    def _lower_values(self, query):
        return {key: value.lower() if isinstance(value, str) else value for key, value in query.items()}

    def _validate_resource(self, resource_name, schema, query):
        tested_query = schema.load(query)
        try:
            self.translator.get_item(resource_name).validate(self.valid_query)
            # self.translator.get_item(resource_name).translate(query)
            self.valid_queries.update({resource_name: schema.dump(tested_query)})
        finally:
            pass

    def _prepare_valid_query(self, query):
        self.org_query = query
        lower = self._lower_values(query)
        try:
            self.valid_query = self.resources_schemas.get_item('ccsi').load(lower)
        finally:
            pass

    def _select_resources(self):
        """select resource by query parameters"""
        for resource_name, schema in self.resources_schemas.items.items():
            if resource_name != 'ccsi':
                try:
                    self._validate_resource(resource_name, schema, self.valid_query)
                except Exception:
                    pass

    def _translate(self):
        """translate from ccsi into resource api"""
        if self.valid_queries:
            for resource_name, query in self.valid_queries.items():
                self.translated_queries.update({resource_name: self.translator.get_item(resource_name).translate(query)})

    def _request(self):
        for resource_name, query in self.translated_queries.items():
            status_code, content = self.connection.get_item(resource_name).send_query(query)
            if status_code == 200:
                self.responses.update({resource_name: content})
            else:
                self.errors.update({resource_name: {status_code : content.decode('utf-8')}})

    def _parse(self):
        for resource_name, response in self.responses.items():
            self.feeds.update({resource_name: self.parser.get_item(resource_name).parse(response)})
