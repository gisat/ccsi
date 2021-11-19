from ccsi import init_storage
from ccsi.storage import storage
from ccsi.resource.query import QueryResource
from ccsi.resource.output import AllResourceXMLResponse, ResourceXMLResponse, ResponseXMLTagSchema
from ccsi.config import Config
from ccsi.resource.parser import FeedSchema


class FakeRequest:

    def __init__(self, query):
        self.args=query
        self.url_root = 'foo.bar/atom'


if __name__ == '__main__':
    init_storage()
    # query = {
    #          'sensorMode': 'ew',
    #          'polarisationChannels': 'hh/hv',
    #          'orbitDirection': 'ascending',
    #          'timeStart': '2017-10-10',
    #          'timeEnd': '2018-10-10',
    #          'bbox': '14.295344355809593,49.999634756552354,14.635223520987124,50.15458581416696',
    #          'collection': 'sentinel-1',
    #          'productType': 'grd',
    #          'processingLevel': 'level1',
    #          'startIndex': 2,
    #          'maxRecords': 1}

    # query = {
    #          'timeStart': '2017-10-10',
    #          'timeEnd': '2018-10-10',
    #          'bbox': '14.295344355809593,49.999634756552354,14.635223520987124,50.15458581416696',
    #          'productType': 'wta',
    #          'orbitDirection: 'ascending'
    #          'orbitNumber': }
    #
    query = {
             'processingDate': '2018-10-10',
             'custom:cs3dataset': 'mean_sea_level_pressure',
             'productType': 'reanalysis',
             'custom:format': 'netcdf'}

    #
    request = FakeRequest(query)
    resource_name = 'wekeo_c3s'

    # resource
    from ccsi.storage import storage
    from ccsi.resource.output import ResourceJsonResponse, ResourceXMLResponse
    query_processor = QueryResource(storage.resource_schemas, storage.translator, storage.connection, storage.parser)
    query_processor.process_query(request.args, resource_name=resource_name)
    # # import json
    # # with open("C:\michal\gisat\projects\Cure\junk\wekeo_content.json", 'r') as file:
    # #     content = json.load(file)
    # #
    # # query_processor.responses.update({'wekeo_s1': content})
    # # query_processor._parse()
    # response = ResourceJsonResponse(FeedSchema, query_processor)
    # response.build_response()
    if len(query_processor.errors) > 0:
        {'message': query_processor.errors}, 500


    response = ResourceXMLResponse(FeedSchema, ResponseXMLTagSchema, storage.response_specification,
                                   Config.NAMESPACES, query_processor, 'url', resource_name)
    response.build_response()

    #

    # all
    #
    # feed_schema=FeedSchema()


    # try:
    #     query_processor.process_query(request.args)
    # except Exception as error:
    #     print(error)
    # response = JsonResponse(FeedSchema, query_processor)
    # response.build_response()
    #
    #     from ccsi.storage import storage
    #     new = storage.translator.get_item(resource_name).translate(query, )
    #     print(new)
    #     pass
    #
    #     from ccsi.storage import storage
    #     wekeo = storage.connections.get_item('wekeo_s1')
    #
    #     body = {
    #   "datasetId": "EO:ESA:DAT:SENTINEL-1:SAR",
    #   "boundingBoxValues": [
    #     {
    #       "name": "bbox",
    #       "bbox": [
    #         14.295344355809593,
    #         49.999634756552354,
    #         14.635223520987124,
    #         50.15458581416696
    #       ]
    #     }
    #   ],
    #   "dateRangeSelectValues": [
    #     {
    #       "name": "position",
    #       "start": "2014-10-06T00:00:00.000Z",
    #       "end": "2021-04-18T00:00:00.000Z"
    #     }
    #   ],
    #   "stringChoiceValues": [
    #     {
    #       "name": "productType",
    #       "value": "GRD"
    #     }
    #   ]
    # }
    #
    #     response = wekeo.send_query(body)
    #     pass
#
# # testovani db
#
#     user = {
#     "username" : "test_user",
#     "email" : "email@test.test",
#     "password" : "pwd"
#     }
#
# dataset = {
#     "datasetName" : "test_dataset"
#
# }



# query = {
#     'datasetId': 'EO:EUM:DAT:SENTINEL-3:OL_2_WFR___',
#
#     'limit': 1000,
#     'offset': 0,
#     'start_date': '2016-09-02',
#     'end_date': '2021-01-02'
# }
# query = {
#     'datasetId': 'EO:CLMS:DAT:CORINE',
#     'limit': 1000,
#     'offset': 0,
#     'start_date': '2016-09-02',
#     'end_date': '2021-01-02'
# }
#
#
#
# from ccsi.cache.cache import WekeoCache
# c = WekeoCache('https://wekeo-broker.apps.mercator.dpi.wekeo.eu/databroker', "")
# r = c.send_querycatalogue(query)
# print(len(r))