from dataclasses import dataclass, field
from typing import Optional, List, Union, Any

from ccsi.base import Singleton, Container
from ccsi.resource.parameters import ResourcesParametersContainer, QuerySchemaBuilder, ResourceSchemasContainer
from ccsi.resource.proxy import proxy_container, Proxy
from ccsi.errors.handlers import Errors
from ccsi.resource.output import Description, ResponseSpecContainer
from ccsi.config import Config


class Storage(metaclass=Singleton):
    """Storage for containers"""

    def __init__(self):
        self.response_specification = ResponseSpecContainer()
        self.resources_parameters = ResourcesParametersContainer()
        self.query_schema_builder = QuerySchemaBuilder()
        self.errors = Errors()
        self.resource_schemas = ResourceSchemasContainer()
        self.description = Description(Config.NAMESPACES, self.resources_parameters)
        self.proxy = proxy_container

    def add_container(self, name: str, container: Container) -> None:
        setattr(self, name, container)

    def get_container(self, name: str) -> Container:
        return getattr(self, name)


storage = Storage()


# helpers functions
def extract_from_storage(container_name: str, item_name: str, parameter_name: Optional[Union[str, List[str]]]) -> Any:
   pass


