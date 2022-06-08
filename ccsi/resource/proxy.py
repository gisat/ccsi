from requests import post, get
from requests.auth import HTTPBasicAuth
from dataclasses import dataclass, field
from ccsi.config import Config
from flask import Response, jsonify, redirect
from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict


class OrderStatus(Enum):
    PENDING = 1
    READY = 2
    FAILED = 3
    AVAILABLE = 4


class Proxy(ABC):

    @abstractmethod
    def process(self, process_id):
        pass


@dataclass
class OndaProxy(Proxy):
    pwd: str = field(default=Config.ONDA_PWD)
    user: str = field(default=Config.ONDA_USER)

    @property
    def auth(self):
        return HTTPBasicAuth(username=self.user, password=self.pwd)

    def order(self, product_id)-> OrderStatus:
        order = f'https://catalogue.onda-dias.eu/dias-catalogue/Products({product_id})/Ens.Order'
        response = post(url=order, auth=self.auth)
        content = response.json()
        if response.status_code == 200 and content.get('Status') == 'RUNNING':
            msg = self.pending()
        elif response.status_code == 403 and content.get('code') == '001':
            msg = self.pending()
        else:
            msg = self.failed()
        return msg

    def check_availibility(self, product_id) -> OrderStatus:
        request = get(f'https://catalogue.onda-dias.eu/dias-catalogue/Products({product_id})')

        if request.status_code != 200:
            return OrderStatus.FAILED
        elif request.status_code == 200 and request.json().get('offline'):
            return OrderStatus.AVAILABLE
        elif request.status_code == 200 and request.json().get('downloadable'):
            return OrderStatus.READY

    def download(self, product_id):
        request = redirect(f'https://catalogue.onda-dias.eu/dias-catalogue/Products({product_id})/$value', code=301)
        self.auth(request)
        return request
        # return Response(response.content, status=response.status_code, content_type=response.headers['content-type'])

    def pending(self, *args, **kwargs):
        return Response("{'status': 'pending'}", 202, content_type='application/json')

    def failed(self, *args, **kwargs):
        return Response({'status': 'failed'}, 400, content_type='application/json')

    def process(self, product_id: str):

        status = self.check_availibility(product_id)
        func = self.resolve_status(status)
        return func(product_id)

    def resolve_status(self, status: OrderStatus):
        if status == OrderStatus.AVAILABLE:
            return self.order
        elif status == OrderStatus.PENDING:
            return self.pending
        elif status == OrderStatus.READY:
            return self.download
        elif status == OrderStatus.FAILED:
            return self.failed


@dataclass
class ProxyContainer:
    container: Dict[str, Proxy] = field(default_factory=dict)

    def add(self, proxy_name: str, proxy: Proxy) -> None:
        self.container.update({proxy_name: proxy})

    def __call__(self, proxy_name: str, product_id: str):
        return self.container.get(proxy_name).process(product_id)


proxy_container = ProxyContainer()
proxy_container.add(proxy_name='onda_s3_proxy', proxy=OndaProxy())






