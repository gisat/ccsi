from requests import get
from marshmallow import Schema, fields, post_load
from marshmallow.validate import OneOf
from ccsi.base import ExcludeSchema, Container
from ccsi.config import Config
from requests.auth import HTTPBasicAuth
from collections import OrderedDict


class Connection:
    """Class represents each registered service. Its base url, parameters, auth etc."""

    def __init__(self, url, typ):
        self.url = url
        self.typ = typ

    def send_request(self, query: dict):
        """sending the request to resource. query is ad dict with resource compatible parameters and respective values"""
        for i in range(Config.connections_repeat):
            while True:
                response = self.request(query)
                if response.status_code == 200:
                    return response.status_code, response
                else:
                    continue
        return response.status_code, response

    def request(self, query):
        return get(self.url, params=query)


CONNECTION_TYPES = {'simple_request': Connection}


class ConnectionSchema(ExcludeSchema):
    url = fields.Url(required=True, allow_none=True)
    typ = fields.String(required=True, validate=OneOf(CONNECTION_TYPES), allow_none=True)

    @post_load()
    def make_connections(self, data, **kwargs):
        if data['typ']:
            typ = CONNECTION_TYPES.get(data['typ'])
            return typ(**data)
        else:
            return None


class ConnectionContainer(Container):

    def __init__(self, connections_schema):
        super(ConnectionContainer, self).__init__()
        self.connection_schema = connections_schema

    def create(self, resource_name, parameters):
        connections = self.connection_schema().load(parameters)
        self.update(resource_name, connections)