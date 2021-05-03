class Config:

    response_form = ['atom', 'json']

    resource_definition = ['ccsi.yaml', 'mundi_s1.yaml']

    connections_repeat = 3

    namespaces = {'atom': {'atom': 'http://a9.com/-/spec/opensearch/1.1/'},
                  'os': {'os': 'http://a9.com/-/spec/opensearch/1.1/'},
                  'eo': {'eo': 'http://a9.com/-/opensearch/extensions/eo/1.0/'},
                  'geo': {'geo': 'http://a9.com/-/opensearch/extensions/geo/1.0/'},
                  'time': {'time': 'http://a9.com/-/opensearch/extensions/time/1.0/'},
                  'ccsi': {'ccsi': 'http://spec/ccsi/parameters'},
                  'param': {'param': 'http://a9.com/-/spec/opensearch/extensions/parameters/1.0/'},
                  'media': {'media': 'http://search.yahoo.com/mrss/'},
                  'georss': {'georss': 'http://www.georss.org/georss'},
                  'dc': {'dc': 'http://purl.org/dc/elements/1.1/'}
                  }


