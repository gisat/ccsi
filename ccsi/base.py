import yaml
from marshmallow import Schema, EXCLUDE, post_dump, RAISE
from flask import abort


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Container(metaclass=Singleton):
    """container for items"""

    def __init__(self, items=None):
        if items is None:
            self.items = {}
        else:
            self.items = items

    def get_item(self, item_name: str):
        return self.items[item_name]

    def get_item_list(self) -> dict:
        return {"items": [item_name for item_name in self.items.keys()]}

    def update(self, item_name: str, item) -> None:
        """update or create resource parameters from definitions"""
        self.items.update({item_name: item})

    def delete(self, item_name: str) -> None:
        self.items.pop(item_name)

    def create_item(self, resource_name, parameters, schema, *args) -> None:
        if schema is None:
            item = parameters
        else:
            item = schema().load(parameters)
        try:
            self.update(resource_name, item(*args))
        except TypeError:
            self.update(resource_name, item)


class ContainerFactory:

    @staticmethod
    def create(container: Container, container_type) -> Container:
        return type(container_type, (container,), {})()


class ExcludeSchema(Schema):
    """ base marshmallow schema with implicit exclude"""
    class Meta:
        unknown = EXCLUDE


class ResourceQuerySchema(Schema):
    """base schema for query processing"""

    @post_dump()
    def remove_skip_values(self, data, **kwargs):
        return {
            key: value for key, value in data.items()
            if value is not None
        }

    class Meta:
        unknown = EXCLUDE
        load_only = ['resource', 'collection']


class WekeoQuerySchema(Schema):
    """base schema for query processing"""

    @post_dump()
    def remove_skip_values(self, data, **kwargs):
        return {
            key: value for key, value in data.items()
            if value is not None
        }

    class Meta:
        unknown = EXCLUDE
        load_only = ['resource']


class CCSIQuerySchema(Schema):
    """base schema for query processing"""

    @post_dump()
    def remove_skip_values(self, data, **kwargs):
        return {
            key: value for key, value in data.items()
            if value is not None
        }

    class Meta:
        unknown = RAISE
        load_only = ['resource', 'collection']

# functions
def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    return data


def validate_regpars(classchema, parameter, regpars):
    schema = classchema(partial=False)
    try:
        schema.load(regpars[parameter])
    except Exception as e:
        return abort(400, {parameter: str(*e.messages['_schema'])})
    return regpars[parameter]


def partial(func, /, *args, **keywords):
    def newfunc(*fargs, **fkeywords):
        newkeywords = {**keywords, **fkeywords}
        return func(*args, *fargs, **newkeywords)
    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc