class Config:

    DEBUG = False

    RESPONSE_FORM = ['atom', 'json']

    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'

    SECRET_KEY = '040fe809dbfe094436096637d79ca93b'

    RESOURCE_DEFINITIONS = ['ccsi.yaml', 'creodias_s1.yaml', 'creodias_s2.yaml', 'creodias_s3.yaml', 'creodias_s5.yaml',  'creodias_landsat8.yaml',
                            'wekeo_s1.yaml', 'wekeo_s2.yaml', 'wekeo_s3.yaml', 'wekeo_c3s.yaml', 'wekeo_cams.yaml', 'cams_eac4.yaml',
                             'cds_era5.yaml', 'onda_s3.yaml', 'wekeo_clms.yaml']


    ADS_KEY = '8585:21c4d84c-f6ec-4de0-a0ec-ab0c096b2b93'

    CDS_KEY = '47967:580c1363-60a1-456d-8fd8-05d902c854d3'

    connections_repeat = 3

    NAMESPACES = {'atom': {'atom': 'http://a9.com/-/spec/opensearch/1.1/'},
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

    SWAGGER = {
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

    WEKEO_API_KEY = 'bW9wbGV0YWw6U0ZSeWZ2bTdWMzZT'

    ONDA_USER = 'michal.opletal@gmail.com'

    ONDA_PWD = '52XM&*3L$TBK4T92MjcG'
