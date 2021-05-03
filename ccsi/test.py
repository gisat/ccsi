from ccsi.storage import storage
from ccsi.config import Config
from pathlib import Path
from ccsi.base import load_yaml

def init_params_container():
    for file in Config.resource_definition:
        path = Path(__file__).parent.joinpath('definitions', file)
        definitions = load_yaml(path)
        storage.resources_parameters.create(definitions['resource_name'])

def init_params():
    for file in Config.resource_definition:
        path = Path(__file__).parent.joinpath('definitions', file)
        definitions = load_yaml(path)

    for name, properties in definitions.get('parameters').items():
        storage.resources_parameters.get_item(definitions.get('resource_name')).update(name, properties)


init_params_container()
init_params()

pass