from flask import Flask
from flaskext.markdown import Markdown
from pathlib import Path
from flasgger import Swagger

from ccsi.config import Config
from ccsi.storage import storage
from ccsi.base import load_yaml
from ccsi.resource.connection import ConnectionSchema
from ccsi.resource.output import ResourceDescriptionSchema
from lxml.etree import register_namespace


def init_params_container(resource_name):
        storage.resources_parameters.create(resource_name)


def init_params(definitions, resource_name):
        try:
            for name, properties in definitions.get('parameters').items():
                storage.resources_parameters.get_item(definitions.get('resource_name')).update(name, properties)
        except Exception as e:
            raise RuntimeError(f'Initialization of parameters failed: {resource_name}, {name}, {e}')


def init_schemas(definitions, resource_name):
        parameters = definitions.get('parameters')

        try:
            schema = storage.query_schema_builder.build_schema(parameters, resource_name)
        except Exception as e:
            raise RuntimeError(f'Initialization of schemas failed: {resource_name}, {e}')
        storage.resource_schemas.update(resource_name, schema)


def init_connections(definitions, resource_name):
        try:
            storage.connections.create(resource_name, definitions['connection'])
        except Exception as e:
            raise RuntimeError(f'Initialization of connection failed: {resource_name}, {e}')


def init_parsers(definitions, resource_name):
    try:
        storage.parsers.create(resource_name, definitions['parser'])
    except Exception as e:
        raise RuntimeError(f'Initialization of parser failed: {resource_name}, {e}')


def init_response_spec(definitions, resource_name):
    if resource_name == 'ccsi':
        try:
            response = definitions['response']
            storage.response_specification.create(response['parameters'])
        except Exception as e:
            raise RuntimeError(f'Initialization of response specification failed: {resource_name}, {e}')


def init_resource_description(definitions, resource_name):
        try:
            description = ResourceDescriptionSchema().load(definitions)
            storage.resource_description.create(resource_name, description)
        except Exception as e:
            raise RuntimeError(f'Initialization of resource description failed: {resource_name}, {e}')


def register_namespaces(namespace):
    for name, ns in namespace.items():
        for prefix, uri in ns.items():
            register_namespace(prefix, uri)


def init_app():
    for file in Config.resource_definition:
        path = Path(__file__).parent.joinpath('definitions', file)
        definitions = load_yaml(path)
        resource_name = definitions['resource_name']

        init_params_container(resource_name)
        init_params(definitions, resource_name)
        init_schemas(definitions, resource_name)
        init_connections(definitions, resource_name)
        init_parsers(definitions, resource_name)
        init_response_spec(definitions, resource_name)
        init_resource_description(definitions, resource_name)

    register_namespaces(Config.namespaces)


def create_app():
    # initialize app
    app = Flask(__name__)

    # markdown
    Markdown(app)
    # blueprints
    from ccsi.errors.handlers import errors
    from ccsi.search.routes import api_search
    from ccsi.resource.routes import api_resource
    from ccsi.main.routes import main

    # blueprint registration
    # app modules
    app.register_blueprint(errors)
    app.register_blueprint(api_search)
    app.register_blueprint(api_resource)
    app.register_blueprint(main)

    #app data init
    init_app()

    # swagger
    Swagger(app, template=Config.swagger)

    # with app.app_context():
    #     api.init_app(app)

    return app
