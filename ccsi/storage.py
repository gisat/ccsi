from ccsi.base import Singleton
from ccsi.resource.parameters import ResourcesParameters, QuerySchemaBuilder, ResourceSchemasContainer
from ccsi.resource.connection import ConnectionContainer, ConnectionSchema
from ccsi.resource.translators import TranslatorContainer, TranslatorSchema
from ccsi.errors.handlers import Errors
from ccsi.resource.parser import ParserContainer, ParserSchema
from ccsi.resource.output import Description, ResponseSpecContainer, ResourceDescriptionContainer
from ccsi.config import Config


class Storage(metaclass=Singleton):
    """Storage for containers"""

    resources_parameters = ResourcesParameters()
    query_schema_builder = QuerySchemaBuilder()
    resource_schemas = ResourceSchemasContainer()
    translator = TranslatorContainer(TranslatorSchema)
    connections = ConnectionContainer(ConnectionSchema)
    errors = Errors()
    parsers = ParserContainer(ParserSchema())
    description = Description(Config.namespaces, resources_parameters)
    response_specification = ResponseSpecContainer()
    resource_description = ResourceDescriptionContainer()



storage = Storage()
