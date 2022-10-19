from requests import post, get
from requests.auth import HTTPBasicAuth
from dataclasses import dataclass, field
from ccsi.config import Config
from flask import Response
from enum import Enum
from abc import ABC, abstractmethod
from typing import Dict
from datetime import datetime
from io import BytesIO

from ccsi.resource.cache import onda_order_cache

class OrderStatus(Enum):
    PENDING = 1
    READY = 2
    FAILED = 3
    AVAILABLE = 4
    TOO_MUCH_REQUEST = 5


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

    def order(self, product_id) -> OrderStatus:
        order = f'https://catalogue.onda-dias.eu/dias-catalogue/Products({product_id})/Ens.Order'
        response = post(url=order, auth=self.auth)
        if response.status_code == 200:
            msg = self.pending()
            onda_order_cache.add_order(orderID=product_id, time=datetime.now())
        elif response.status_code == 429:
            msg = self.too_mucch_request()
        elif 500 > response.status_code >= 400:
            msg = self.pending()
        else:
            msg = self.failed()
        return msg

    def check_availibility(self, product_id) -> OrderStatus:
        response = get(f'https://catalogue.onda-dias.eu/dias-catalogue/Products({product_id})')
        if response.status_code != 200:
            return OrderStatus.FAILED
        elif response.status_code == 200 and response.json().get('offline') and not onda_order_cache.exits(product_id):
            return OrderStatus.AVAILABLE
        elif response.status_code == 200 and response.json().get('offline') and onda_order_cache.exits(product_id):
            return OrderStatus.PENDING
        elif response.status_code == 200 and response.json().get('downloadable'):
            return OrderStatus.READY

    def download(self, product_id):
        url = f'https://catalogue.onda-dias.eu/dias-catalogue/Products({product_id})/$value'
        r = get(url=url, auth=self.auth, stream=True)
        if onda_order_cache.exits(orderID=product_id):
            onda_order_cache.del_order(orderID=product_id)
        return Response(r, content_type=r.headers['Content-Type'])

    def pending(self, *args, **kwargs):
        return Response("{'status': 'pending'}", 201, content_type='application/json')

    def failed(self, *args, **kwargs):
        return Response("{'status': 'failed'}", 400, content_type='application/json')

    def too_mucch_request(self, *args, **kwargs):
        return Response("{'status': 'too much requests'}", 429, content_type='application/json')

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
proxy_container.add(proxy_name='onda_s3', proxy=OndaProxy())






