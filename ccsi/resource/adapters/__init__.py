from pydantic import BaseModel, Field
from typing import Type, Any
from abc import ABC, abstractmethod


class AdapterABC(ABC, BaseModel):

    class Config:
        arbitrary_types_allowed = True


from ccsi.resource.adapters.wekeo import WekeoHRVPP, WekeoCLMSDEM

class AdapterFactory(BaseModel):
    adapters: dict = Field(default_factory=dict)

    def add(self, adapter_name: str, adpter: Type[AdapterABC]) -> None:
        self.adapters.update({adapter_name: adpter})

    def get(self, adapter_name: str, **ignore) -> Type[AdapterABC]:
        return self.adapters[adapter_name]


adapters_factory = AdapterFactory()
adapters_factory.add(adapter_name='wekeo_hrvpp', adpter=WekeoHRVPP)
adapters_factory.add(adapter_name='wekeo_clms_dem', adpter=WekeoCLMSDEM)