from abc import ABC, abstractmethod
from requests import post, get
import json
from marshmallow import fields, post_load
from marshmallow.validate import OneOf

from ccsi.config import Config
from ccsi.base import ExcludeSchema, Container

class Cache(ABC):

    @abstractmethod
    def build_cache(self):
        pass

    @abstractmethod
    def refresh_cache(self):
        pass

    @abstractmethod
    def from_cache(self):
        pass


class WekeoCache(Cache):

    def __init__(self, url, typ):
        self.url = url
        self.typ = typ
        self.get_authorization_header()

    def build_cache(self, dataset):
        pass

    def refresh_cache(self):
        pass


    def from_cache(self):
        pass

    def get_authorization_header(self) -> dict:
        headers = {'Authorization': f'Basic {Config.WEKEO_API_KEY}'}
        response = get(self.url + '/gettoken', headers=headers)
        if response.status_code == 200:
            access_token = json.loads(response.text)['access_token']
            self.auth = {'Authorization': 'Bearer ' + access_token, 'Accept': 'application/json'}
        else:
            raise ValueError(f"Error: Cannot receive Wekeo auth token. Unexpected response {response}.")

    def send_querycatalogue(self, query: dict):
        """sending the query to WHA catalogue"""
        datasetId = query.pop("datasetId")
        response = post(self.url + f'/catalogue/{datasetId}/querycatalogue', headers=self.auth, params=query, json={})
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            self.get_authorization_header()
            return self.send_querycatalogue(query)


class CacheSchema(ExcludeSchema):
    TYPES = {'wekeo_cache': WekeoCache}

    url = fields.Url(required=True, allow_none=True)
    typ = fields.String(required=True, validate=OneOf(TYPES), allow_none=True)

    @post_load()
    def make_class(self, data, **kwargs):
        if data['typ']:
            typ = self.TYPES.get(data['typ'])
            return typ(**data)
        else:
            return None


class CacheContainer(Container):

    def __init__(self, schema):
        super(CacheContainer, self).__init__()
        self.schema = schema

    def create(self, resource_name, parameters):
        item = self.schema().load(parameters)
        self.update(resource_name, item)