class Config:

    response_form = ['atom', 'json']

    resource_definition = ['ccsi.yaml', 'mundi_s1.yaml', 'mundi_s2.yaml', 'mundi_s3.yaml', 'mundi_clms.yaml',
                           'creodias_s1.yaml', 'creodias_s3.yaml']

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
                  'dc': {'dc': 'http://purl.org/dc/elements/1.1/'},
                  'resto': {'resto': "http://mapshup.info/-/resto/2.0/"}
                  }

    swagger = {
              "swagger": "2.0",
              # "openapi": "3.0.2",
              "info": {
                "title": "Copernicus Core Service Interface",
                "description": "API for CCSI",
                "contact": {
                  "responsibleOrganization": "Gisat s.r.o",
                  "responsibleDeveloper": "Michal Opletal",
                  "email": "michal.opletal@gisat.cz",
                  "url": "www.gisat.cz",
                },
                "version": "0.8.0"
              }
            }

