import os
import json
from concurrent.futures.thread import ThreadPoolExecutor
from time import time, sleep as timesleep
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from requests import get, Response
import argparse
import geopandas as gpd
from pydantic import BaseModel, Field, PrivateAttr, validator
from typing import Optional, List, Literal, Union, Type, Dict
from uuid import uuid4, UUID
from enum import Enum
from pathlib import Path
from termcolor import colored


# constants
# BASE_URL = "http://185.226.13.104"
BASE_URL = "http://localhost:5000"


# helper func
def create_fld_if_not_exist(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)


# base classes
class BaseModelSetter(BaseModel):

    class Config:
        allow_mutation = True


class BaseModelPartialEQ(BaseModel):

    def __eq__(self, other: BaseModel):
        return all([sv == other.__dict__[sk] for sk, sv in self.__dict__.items() if sv is not None])


# schema
class Attrib(BaseModelSetter, BaseModelPartialEQ):
    href: Optional[str]
    rel: Optional[str]
    type: Optional[str]


class Tag(BaseModelSetter, BaseModelPartialEQ):
    tag: str
    text: Optional[str]
    attrib: Optional[Attrib]


class Entry(BaseModelSetter, BaseModelPartialEQ):
    entry: List[Tag] = Field(default_factory=list)


class Feed(BaseModelSetter):
    entries: List[Entry] = Field(default_factory=list)
    head: Optional[List[Tag]] = Field(default_factory=list)
    totalResults: int = Field(default=0)


# schema
class JsonCCSISchema(BaseModelSetter):
    feed: Optional[Feed]
    _level: Literal['entries', 'tags'] = PrivateAttr(default='entries')

    def __iter__(self):
        """iter trought certain level """
        for entry in self.feed.entries:
            if self._level == 'entries':
                yield entry
            for tag in entry.entry:
                if self._level == 'tags':
                    yield tag

    @validator('feed', pre=True)
    def unpack_feed(cls, value):
        if isinstance(value, list):
            return value[0]
        elif isinstance(value, Feed):
            return value

    def __next__(self):
        return self

    def __call__(self, level: Literal['feeds', 'entries', 'tags'] = 'tags'):
        self._level = level
        return self


# paraser and download
class STATUS(Enum):
    READY = 1
    PENDING = 2
    FAILED = 3
    TOO_MUCH_REQUESTS = 4


# resource dataclass
class Resource(BaseModelSetter):
    link: Optional[str]
    title: Optional[Union[str, UUID]]
    response: Optional[Response] = Field(default=None)
    status: Optional[STATUS] = Field(default=STATUS.PENDING)
    index: int

    @validator('title', pre=True)
    def set_title(cls, title):
        if not title:
            return uuid4()
        return title

    class Config:
        arbitrary_types_allowed = True


class Parser:

    def __call__(self, feeds: JsonCCSISchema) -> List[Resource]:
        resources = []
        for index, entry in enumerate(feeds):
            link, title = None, None
            for tag in entry.entry:
                if tag.tag == 'link' and tag.attrib.rel == 'enclosure':
                    link = tag.attrib.href
                elif tag.tag == 'title':
                    title = tag.text
            resources.append(Resource(link=link, title=title, index=index))

        return resources


#  request and download

class CCSIRequester(BaseModel):
    resource: str
    params: Optional[Union[dict, BaseModel]]
    schemas: Type[JsonCCSISchema]
    parser: Parser
    records: List[Resource] = Field(default_factory=list)

    @validator('params', pre=True)
    def set_params(cls, value):
        if isinstance(value, BaseModel):
            return value.dict(by_alias=True)
        elif isinstance(value, dict):
            return value

    def run(self) -> List[Resource]:
        response = self.send_request()
        feed = self.parse_response(response)
        self.parse_feed(feed)
        self.get_next(feed)
        return self.records

    def parse_feed(self, feed: JsonCCSISchema):
        self.records += self.parser(feed)

    def parse_response(self, response: Response)-> JsonCCSISchema:
        return self.schemas(feed=response.json())

    def get_next(self, feed: JsonCCSISchema)-> None:
        for tag in feed.feed.head:
            if Tag(tag='link', attrib=Attrib(rel='next')) == tag:
                next = tag
        # if any(next:=tag for tag in feed.feed.head if Tag(tag='link', attrib=Attrib(rel='next')) == tag):
        if len(self.records) == feed.feed.totalResults:
            return None
        response = get(url=next.attrib.href)
        feed = self.parse_response(response)
        self.parse_feed(feed)
        self.get_next(feed)

    def send_request(self):
        response = get(url=f"{BASE_URL}/{self.resource}/json/search?", params=self.params)
        print(response.url)
        if response.status_code != 200:
            raise Exception(f"ccsi request {response.url} failed")
        return response

    class Config:
        arbitrary_types_allowed = True


def request_resource(resource: Resource) -> Resource:
    print(f' {resource.index} requested from {resource.link}')
    resource.response = get(resource.link, allow_redirects=True, stream=True)
    return resource


def resolve_status(resource: Resource) -> Resource:

    if resource.response.status_code == 200:
        print(colored(f' {resource.index} requested from {resource.link} : data ready', 'green'))
        resource.status = STATUS.READY
    elif resource.response.status_code == 201:
        print(colored(f' {resource.index} requested from {resource.link} : data pending', 'blue'))
        resource.status = STATUS.PENDING
    elif resource.response.status_code == 429:
        print(colored(f'{resource.index} requested from {resource.link} : data too much requests', 'red'))
        resource.status = STATUS.TOO_MUCH_REQUESTS
    else:
        resource.status = STATUS.FAILED
        print(colored(f' {resource.index} requested from {resource.link} : failed', 'red'))

    return resource


def download(path: Path, resource: Resource):
    print(colored(f' {resource.index} requested from {resource.title} : data download start', 'green'))
    with open(path / resource.title, 'wb') as fd:
        fd.write(resource.response.content)
        # for count, chunk in enumerate(resource.response.iter_content()):
        #     fd.write(chunk)
        #     print(colored(f' {resource.index} requested from {resource.title} : data download {count} cnunk', 'green'))
    print(colored(f' {resource.index} requested from {resource.title} : data download end', 'green'))


class Downloader(BaseModel):
    pool: List[Resource]
    path: Path
    sleep: int = Field(default=200)
    sleep_step: int = Field(default=5)
    timeout: int = Field(default=12*60)
    max_worker: int = Field(default=20)

    def run(self):
        with ThreadPoolExecutor(max_workers=20) as executor:
            executor.map(self.request_data, self.pool)

    def sequential_run(self):
        for resource in self.pool:
            self.request_data(resource)

    def request_data(self, resource: Resource) ->None:
        time = 0
        while resource.status in [STATUS.PENDING, STATUS.TOO_MUCH_REQUESTS] or time <= self.timeout:
            request_resource(resource)
            resolve_status(resource)

            if resource.status == STATUS.READY:
                download(self.path, resource)
                break
            elif resource.status == STATUS.TOO_MUCH_REQUESTS or resource.status == STATUS.PENDING:
                timesleep(self.sleep)
                print(f' {resource.index} requested from {resource.link} : sleep for {self.sleep} s')
                time += self.sleep
            elif resource.status == STATUS.FAILED:
                break

    class Config:
        arbitrary_types_allowed = True


# user input
class UserInput(BaseModel):
    Start: str = Field(alias='timeStart')
    End: str = Field(alias='timeEnd')
    ID: Optional[str]
    Output: Path
    Geometry: str = Field(alias='bbox')
    Resources: Dict[str, Dict[str, str]]

    @validator('Output', 'Geometry', pre=True)
    def set_output(cls, value):
        return Path(value)

    @validator('Geometry', pre=True)
    def set_bbox(cls, value) -> str:
        return ','.join([str(v) for v in list(gpd.read_file(value).total_bounds)])

    class Config:
        allow_population_by_field_name = True


# ccsi params setting
# following classes define a CCSI params and also allows to be expand for converting and validation
class PageingSetting(BaseModel):
    maxRecords: str = Field(default='50')
    startIndex: str = Field(default='0')


class WekeoS2Input(PageingSetting):
    processingLevel: str
    bbox: str
    timeStart: str
    timeEnd: str


class CDSERA5Input(PageingSetting):
    customcamsDataset: str = Field(alias='custom:camsDataset')
    customformat: str = Field(alias='custom:format')
    bbox: str
    timeStart: str
    timeEnd: str

    class Config:
        allow_population_by_field_name = True


class ONDAS3Input(PageingSetting):
    productType: str
    bbox: str
    timeStart: str
    timeEnd: str


RESOURCES = {'wekeo_s2': WekeoS2Input,
             'cds_era5': CDSERA5Input,
             'onda_s3': ONDAS3Input}

if __name__ == "__main__":

    # # I little bit change a CLI for testing but i thinh that is not problem to change the code as you need.
    cli = argparse.ArgumentParser(description="This script produces LST of App 1")
    cli.add_argument("-c", "--City", type=str, metavar="", required=True,
                        help="City name (Berlin, Copenhagen, Heraklion, Sofia)")
    cli.add_argument("-s", "--Start", type=str, metavar="", required=True,
                        help="Start Date e.g. 2019-01-01")
    cli.add_argument("-e", "--End", type=str, metavar="", required=True,
                        help="End Date e.g. 2019-01-190")
    cli.add_argument("-i", "--ID", type=str, metavar="", required=True,
                        help="Order/Run ID")
    cli.add_argument("-o", "--Output", type=str, metavar="", required=True,
                        help="Path to the output directory")
    cli.add_argument("-g", "--Geometry", type=str, metavar="", required=True,
                        help="Path to the geometry with AOI (geojsons)")
    cli.add_argument("-r", "--Resources", type=str, metavar="", required=True,
                        help="Dictionary of resources")

    # args = cli.parse_args()
    # args = cli.parse_args(['--City', 'Heraklion',
    #                        '--Start', '2020-03-01',
    #                        '--End', '2020-03-31',
    #                        '--Output', '/home/schmid/Desktop/test',
    #                        '--Geometry',
    #                        '/media/schmid/One Touch1/Documents/WORK/Projects/Cure/cities/Heraklion.geojson',
    #                        '--Resources', '{\"onda_s3\": {\"productType\": \"rbt\"},'
    #                                       '\"wekeo_s2\": {\"processingLevel\": \"level2a\"},'
    #                                       '\"cds_era5\": {\"customcamsDataset\": \"total_column_water_vapour,10m_v_component_of_wind\", \"customformat\": \"grib\"}}',
    #                        '--ID', '123456789'])
    args = cli.parse_args(['--City', 'Heraklion',
                           '--Start', '2021-05-01',
                           '--End', '2021-08-30',
                           '--Output', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion',
                           '--Geometry', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion\Heraklion_wgs.geojson',
                           '--Resources', '{"wekeo_s2": {"processingLevel": "level2a"}}',
                           '--ID', '123456789'])
    # args = cli.parse_args(['--City', 'Heraklion',
    #                        '--Start', '2020-03-25',
    #                        '--End', '2020-03-31',
    #                        '--Output', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion',
    #                        '--Geometry', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion\Heraklion_wgs.geojson',
    #                        '--Resources', '{"onda_s3": {"productType": "rbt"}}',
    #                        '--ID', '123456789'])
    # args = cli.parse_args(['--City', 'Heraklion',
    #                        '--Start', '2020-03-01',
    #                        '--End', '2020-03-31',
    #                        '--Output', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion',
    #                        '--Geometry', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion\Heraklion_wgs.geojson',
    #                        '--Resources', '{"cds_era5": {"customcamsDataset": "total_column_water_vapour,10m_v_component_of_wind", "customformat": "grib"}}',
    #                        '--ID', '123456789'])


    start = time()

    # validation of user input
    args.Resources = json.loads(args.Resources)
    print(args.Resources)
    geom_base_directory = args.Geometry
    geometries = {"Berlin": os.path.join(geom_base_directory, "Berlin.geojson"),
                  "Copenhagen": os.path.join(geom_base_directory, "Copenhagen.geojson"),
                  "Heraklion": os.path.join(geom_base_directory, "Heraklion.geojson"),
                  "Sofia": os.path.join(geom_base_directory, "Sofia.geojson")}
    # args.Geometry = geometries[args.City]
    user_input = UserInput(**vars(args))

    for resource, extra_params in user_input.Resources.items():
        print(resource)
        output_directory = user_input.Output / resource
        create_fld_if_not_exist(output_directory)

        # setting ccsi params and requesting the data
        extra_params.update(user_input.dict(by_alias=True))
        # App1 and App10 need to have two month of S2 data although start date = end date
        if resource == "wekeo_s2" and extra_params["timeStart"] == extra_params["timeEnd"]:
            start_date = extra_params["timeStart"]
            new_start_date = dt.strptime(start_date, "%Y-%m-%d") + relativedelta(months=-2)
            extra_params["timeStart"] = str(new_start_date.date())
        params = RESOURCES.get(resource)(**extra_params)

        requester = CCSIRequester(resource=resource, params=params, schemas=JsonCCSISchema, parser=Parser())
        resource_data = requester.run()

        # download
        downloader = Downloader(pool=resource_data, path=output_directory, sleep=8*60, timeout=12*60, max_worker=1)
        downloader.run()



    end = time()
    print(f'Process time: {end - start} s')
    # first_wvp_date = start_date.replace("-", "") + "T000000"
    # print(first_wvp_date)

