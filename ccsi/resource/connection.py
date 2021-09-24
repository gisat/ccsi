from requests import get, post, Request, Session
from marshmallow import Schema, fields, post_load
from marshmallow.validate import OneOf
from ccsi.base import ExcludeSchema, Container
from ccsi.config import Config
from requests.auth import HTTPBasicAuth
from collections import OrderedDict
from abc import ABC, abstractmethod
from time import sleep
import json
from functools import partial

class Connection(ABC):

    @abstractmethod
    def send_query(self, query: dict):
        pass


class BasicConnection(Connection):
    """Class represents each registered service. Its base url, parameters, auth etc."""

    def __init__(self, url, typ):
        self.url = url
        self.typ = typ

    def send_query(self, query: dict):
        """sending the query to resource. query is ad dict with resource compatible parameters and respective values"""

        response = get(self.url, params=query)
        if response.status_code == 200:
            return response.status_code, response.content
        else:
            raise ConnectionError(f'Problem with connections tu {self.url} \n Status code: {response.status_code} \n'
                                  f'Message: {response.content}')


class WekeoConnection(Connection):
    """Class represents each registered service. Its base url, parameters, auth etc."""

    def __init__(self, url, typ):
        self.url = url
        self.typ = typ
        self.get_authorization_header()

    def send_query(self, query: dict):
        """sending the query to resource. query is ad dict with resource compatible parameters and respective values"""
        query_params = query.pop('query_params', None)
        jobId = self.send_datarequest(query)
        status_code,  response = self.datarequest_status(jobId)
        if status_code == 200:
            result = self.datarequest_results(jobId, query_params)
            result['content'] = self.send_orders(result['content'], jobId)
            return status_code, result
        else:
            return status_code, response.content

    def send_datarequest(self, query: dict):
        response = post(self.url + '/datarequest', headers=self.auth, json=query)
        if response.status_code == 200:
            return response.json()['jobId']
        elif response.status_code == 403:
            self.get_authorization_header()
            return self.send_datarequest(query)

    def datarequest_status(self, jobId):
        while True:
            response = get(self.url + f'/datarequest/status/{jobId}', headers=self.auth)
            if response.status_code == 200 and response.json()['status'] == 'completed':
                return 200, 'Done'
            elif response.status_code == 200 and response.json()['status'] == 'failed':
                return 500, response
            elif response.status_code == 200:
                sleep(5)
            elif response.status_code == 403:
                self.get_authorization_header()
                return self.datarequest_status(self, jobId)

    def datarequest_results(self, jobId, params):
        response = get(self.url + f'/datarequest/jobs/{jobId}/result', headers=self.auth,
                       params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            self.get_authorization_header()
            return self.datarequest_results(jobId, params)

    def send_orders(self, resluts: list, jobId: str ):
        for i in range(len(resluts)):
            body = {"jobId": jobId, "uri": resluts[i]['url']}
            resluts[i]['downloadUri'] = f'{self.url}/dataorder/download/{self.send_order(body)}'
        return resluts


    def send_order(self, order):
        response = post(self.url + '/dataorder', headers=self.auth, json=order)
        if response.status_code == 200:
            return response.json()['orderId']
        elif response.status_code == 403:
            self.get_authorization_header()
            return self.send_order(order)

    def get_authorization_header(self) -> dict:
        headers = {'Authorization': f'Basic {Config.wekeo_api_key}'}
        response = get(self.url + '/gettoken', headers=headers)
        if response.status_code == 200:
            access_token = json.loads(response.text)['access_token']
            self.auth = {'Authorization': 'Bearer ' + access_token, 'Accept': 'application/json'}
        else:
            raise ValueError(f"Error: Cannot receive Wekeo auth token. Unexpected response {response}.")


class ConnectionSchema(ExcludeSchema):
    CONNECTION_TYPES = {'simple_request': BasicConnection,
                        'wekeo_connection': WekeoConnection}

    url = fields.Url(required=True, allow_none=True)
    typ = fields.String(required=True, validate=OneOf(CONNECTION_TYPES), allow_none=True)

    @post_load()
    def make_connections(self, data, **kwargs):
        if data['typ']:
            typ = self.CONNECTION_TYPES.get(data['typ'])
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







