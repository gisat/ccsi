import argparse
import json
import os
from pathlib import Path
from time import time
from typing import Optional, Dict
import geopandas as gpd
from dateutil.relativedelta import relativedelta
from datetime import datetime as dt
from pydantic import BaseModel, Field, validator

from pyccsi import CCSIDownloader


def create_fld_if_not_exist(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

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
    # args = cli.parse_args(['--City', 'Heraklion',
    #                        '--Start', '2021-05-01',
    #                        '--End', '2021-09-30',
    #                        '--Output', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion',
    #                        '--Geometry', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion\Heraklion_wgs.geojson',
    #                        '--Resources', '{"wekeo_s2": {"processingLevel": "level2a"}}',
    #                        '--ID', '123456789'])
    # args = cli.parse_args(['--City', 'Heraklion',
    #                        '--Start', '2020-03-25',
    #                        '--End', '2020-03-31',
    #                        '--Output', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion',
    #                        '--Geometry', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion\Heraklion_wgs.geojson',
    #                        '--Resources', '{"onda_s3": {"productType": "rbt"}}',
    #                        '--ID', '123456789'])
    args = cli.parse_args(['--City', 'Heraklion',
                           '--Start', '2020-03-01',
                           '--End', '2020-03-31',
                           '--Output', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion',
                           '--Geometry', 'C:\michal\gisat\projects\Cure\\app\CURE_APP1_AOIs\Heraklion\Heraklion_wgs.geojson',
                           '--Resources', '{"cds_era5": {"customcamsDataset": "total_column_water_vapour,10m_v_component_of_wind", "customformat": "grib"}}',
                           '--ID', '123456789'])


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

        ccsi = CCSIDownloader(host_url="http://localhost:5000")
        ccsi.send_request(resource=resource, params=params)
        ccsi.download(path=output_directory)


    end = time()
    print(f'Process time: {end - start} s')
    # first_wvp_date = start_date.replace("-", "") + "T000000"
    # print(first_wvp_date)