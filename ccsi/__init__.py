from flask import Flask
from flaskext.markdown import Markdown
from pathlib import Path
from flasgger import Swagger
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_httpauth import HTTPBasicAuth
from lxml.etree import register_namespace


from ccsi.config import Config
from ccsi.storage import storage
from ccsi.base import load_yaml, ContainerFactory, Container
from ccsi.resource.connection import ConnectionSchema
from ccsi.resource.output import ResourceDescriptionSchema
from ccsi.config import Config
from ccsi.cache.cache import CacheSchema
from ccsi.resource.parser import ParserSchema
from ccsi.resource.translators import TranslatorSchema


db = SQLAlchemy()
bcrypt = Bcrypt()
auth = HTTPBasicAuth()


def create_app(config=Config):
    #app storage init
    init_storage()

    # initialize app
    app = Flask(__name__)
    # markdown
    Markdown(app)
    # blueprints
    from ccsi.errors.handlers import errors
    from ccsi.search.routes import api_search
    from ccsi.resource.routes import api_resource
    from ccsi.main.routes import main
    from ccsi.users.routes import api_user

    # blueprint registration
    # app modules
    app.register_blueprint(errors)
    app.register_blueprint(api_search)
    app.register_blueprint(api_resource)
    app.register_blueprint(main)
    app.register_blueprint(api_user)


    # swagger
    Swagger(app, template=config.SWAGGER)

    # db
    app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
    db.init_app(app)

    with app.app_context():
        db.create_all()

    # bcrypt
    bcrypt.init_app(app)

    # register namespaces
    register_namespaces(Config.NAMESPACES)
    return app


#  init func
def init_params_container(resource_name):
    storage.resources_parameters.create(resource_name)


def init_params(definitions, resource_name):
    try:
        for name, properties in definitions.get('parameters').items():
            storage.resources_parameters.get_item(definitions.get('resource_name')).update(name, properties)
    except Exception as e:
        raise RuntimeError(f'Initialization of parameters failed: {resource_name}, {name}, {e}')


def init_response_spec(definitions, resource_name):
    if resource_name == 'ccsi':
        try:
            response = definitions['response']
            storage.response_specification.create(response['parameters'])
        except Exception as e:
            raise RuntimeError(f'Initialization of response specification failed: {resource_name}, {e}')


def init_schemas(definitions, resource_name):
    parameters = definitions.get('parameters')
    try:
        schema = storage.query_schema_builder.build_schema(parameters, resource_name)
    except Exception as e:
        raise RuntimeError(f'Initialization of schemas failed: {resource_name}, {e}')
    storage.resource_schemas.update(resource_name, schema)


def create_container(container_name, parameters, resource_name, schema, *args):
    if not hasattr(storage, container_name):
        container = ContainerFactory.create(Container, container_name)
        storage.add_container(container_name, container)
    try:
        storage.get_container(container_name).create_item(resource_name, parameters, schema, *args)
    except Exception as e:
        raise RuntimeError(f'Initialization of {container_name} container failed: {resource_name}, {e}')


def register_namespaces(namespace):
    for name, ns in namespace.items():
        for prefix, uri in ns.items():
            register_namespace(prefix, uri)


def init_storage():
    for file in Config.RESOURCE_DEFINITIONS:
        path = Path(__file__).parent.joinpath('definitions', file)
        definitions = load_yaml(path)
        resource_name = definitions['resource_name']

        init_params_container(resource_name)
        init_params(definitions, resource_name)
        init_response_spec(definitions, resource_name)
        init_schemas(definitions, resource_name)

        def init_container(definitions, container_name, schema, *args, parameter_name=None):
            if parameter_name:
                parameters = definitions.get(parameter_name)
            else:
                parameters = definitions.get(container_name)

            if parameters is not None:
                create_container(container_name, parameters, resource_name, schema, *args)

        init_container(definitions, 'translator', TranslatorSchema, storage.resources_parameters.get_item(resource_name))
        init_container(definitions, 'connection', ConnectionSchema)
        init_container(definitions, 'parser', ParserSchema)
        init_container(definitions, 'resource_description', ResourceDescriptionSchema)
        init_container(definitions, 'cache', CacheSchema)