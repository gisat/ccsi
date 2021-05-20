from marshmallow import Schema, fields, post_load, pre_load, post_dump, EXCLUDE, ValidationError
from marshmallow.validate import OneOf, ContainsOnly
from shapely import wkt, errors
from shapely.geometry import box
from dateutil.parser import isoparse
from ccsi.base import Container, ExcludeSchema, ResourceQuerySchema, CCSIQuerySchema, partial
# from functools import partial


# transformation
def identity(self, value):
    return value


def offset(self, value, offset):
    return value + offset



TRANSFORMATION_FUNC = {'identity': identity,
                       'offset': offset}


# parameters & translator
class Parameter:

    def __init__(self, name, typ, tranfunc, definitions):
        self.name = name
        self.tranfunc = tranfunc.__get__(self)
        self.typ = typ
        self.definitions = definitions

    def validate(self, value):
        if isinstance(value, str):
            return True
        else:
            raise ValueError(f'{self.__repr__()}: Invalid type of argument {value}, expected {self.__class__.__name__}')

    def transform(self, value):
        new = self.tranfunc(value)
        if self.validate(new):
            return {self.name: new}

    def __repr__(self):
        return f'Parameter {self.name}'


class String(Parameter):

    def __init__(self, name, typ, tranfunc, definitions):
        super().__init__(name, typ, tranfunc, definitions)


class Integer(Parameter):

    def __init__(self, name, typ, tranfunc, definitions):
        super().__init__(name, typ, tranfunc, definitions)

    def validate(self, value):
        if isinstance(value, int):
            return True
        else:
            raise ValueError(f'{self.__repr__()}: Invalid type of argument {value}, expected {self.__class__.__name__}')


class Float(Parameter):

    def __init__(self, name, typ, tranfunc, definitions):
        super().__init__(name, typ, tranfunc, definitions)

    def validate(self, value):
        if isinstance(value, float):
            return True
        else:
            raise ValueError(f'{self.__repr__()}: Invalid type of argument {value}, expected {self.__class__.__name__}')


class Bbox(Parameter):

    def __init__(self, name, typ, tranfunc, definitions):
        super().__init__(name, typ, tranfunc, definitions)

    def validate(self, value):
        try:
            box(*[float(coor) for coor in value.split(',')])
            return True
        except Exception as e:
            raise ValueError(f'{self.__repr__()}: Invalid type of argument {value}, expected bounding box in form '
                             f'of Coordinates in longitude, latitude in order west, south, east, north. CRS is '
                             f'epsg 4326, decimal degree')


class WKTGeom(Parameter):

    def __init__(self, name, typ, tranfunc, definitions):
        super().__init__(name, typ, tranfunc, definitions)

    def validate(self, value):
        try:
            wkt.loads(value)
            return True
        except errors.WKTReadingError:
            raise ValueError(f'{self.__repr__()}: Invalid type of argument {value}, expected WKT fromat)')


class DateTime(Parameter):

    def __init__(self, name, typ, tranfunc, definitions):
        super().__init__(name, typ, tranfunc, definitions)

    def validate(self, value):
        try:
            isoparse(value)
            return True
        except ValueError:
            raise ValueError(f'{self.__repr__()}: Invalid type of argument {value}, expected Date in 8601 fromat)')



class Options(Parameter):
    """class for parametr with options. options is defined as dict. """

    def __init__(self, name, typ, tranfunc, mapping, definitions):
        super().__init__(name, typ, tranfunc, definitions)
        self.mapping = mapping

    def validate(self, value):
        if value in self.mapping:
            return True
        else:
            raise ValueError(f'{self.__repr__()}: Invalid argument {value}, expected one of '
                             f'{", ".join([key for key in self.mapping.keys()])}')

    def transform(self, value):
        new = self.tranfunc(value)
        if self.validate(new):
            return {self.name: self.mapping[value]}


PARAM_TYPES = {'string': String,
              'integer': Integer,
              'float': Float,
              'bbox': Bbox,
              'wktgeom': WKTGeom,
              'datetime': DateTime,
              'option': Options}


class AnyType(fields.Field):
    """Any type """

    def _serialize(self, value, attr, obj, **kwargs):
        return

    def _deserialize(self, value, attr, data, **kwargs):
        return value

class TransFunction(fields.Field):
    """Any type """

    def _serialize(self, value, attr, obj, **kwargs):
        return

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            if value not in TRANSFORMATION_FUNC:
                raise ValidationError(f"Parameter: {data['name']}: Invalid transformation function specification:{value}")
        except TypeError:
            if value['name'] not in TRANSFORMATION_FUNC:
                raise ValidationError(
                    f"Parameter: {data['name']}: Invalid transformation function specification:{value}")

        if isinstance(value, str):
            return TRANSFORMATION_FUNC.get(value)
        elif isinstance(value, dict):
            return partial(TRANSFORMATION_FUNC.get(value['name']), **value['property'])




class ParameterSchema(ExcludeSchema):
    typ = fields.Str(required=True, validate=OneOf(PARAM_TYPES))
    name = fields.Str(required=True)
    tranfunc = TransFunction(required=True)
    mapping = fields.Dict(required=False)
    definitions = fields.Dict(required=True, default=None)


    @pre_load
    def save_definitions(self, data, **kwargs):
        if 'definitions' not in data:
            data.update({'definitions': data.copy()})
        return data

    @post_dump(pass_original=True)
    def extract_definitions(self, data, original_data, many, **kwargs):
        data = data['definitions']
        return data

    @post_load(pass_original=True)
    def make_parameter(self, data, original_data, **kwargs):
        typ = PARAM_TYPES.get(data['typ'])
        data['definitions'] = original_data.get('definitions').copy()
        return typ(**data)


parameterschema = ParameterSchema(dump_only=['definitions'])


# parameters containers
class ResourceParameters:
    """container for individual resource parameters"""

    def __init__(self):
        pass

    def update(self, name, properties):
        setattr(self, name, self._build_parameter(properties))

    def delete(self, name):
        delattr(self, name)

    def get(self):
        return {key: parameterschema.dump(value) for key, value in self.__dict__.items()}

    def get_parameter(self, name):
        if name in self.__dict__.keys():
            return getattr(self, name)
        else:
            raise AttributeError(f'Parameter {name} is not found')

    def get_mapped_pairs(self):
        return {key: value.name for key, value in self.__dict__.items()}

    def _build_parameter(self, properties):
        return parameterschema.load(properties)


class ResourcesParameters(Container):
    """container for set of resource api parameters"""

    def __int__(self):
        super(ResourcesParameters, self).__int__()

    def create(self, resource_name):
        self.items.update({resource_name: ResourceParameters()})

    def update(self, resource_name, parameters):
        for name, properties in parameters.items():
            self.items[resource_name].update(name, properties)


class ParamTranslator:
    """ class responsible for translation from ccsi set o api params to resource api params"""

    def __init__(self, resources_parameters: ResourcesParameters):
        self.resources_parameters = resources_parameters

    def translate(self, resource_name, query: dict):
        """translate from one set of api parameters to another"""
        new_query = {}
        for key, value in query.items():
            new_query.update(self.resources_parameters.get_item(resource_name).get_parameter(key).transform(value))
        return new_query

    def get_mapped_pairs(self, resource_name):
        return self.resources_parameters.get_item(resource_name).get_mapped_pairs()


#  parameters schemas
# validations
def validate_choises(value, choises):
    if isinstance(value, str):
        if not any(item in value.split(',') for item in choises):
            return False

def validate_datetime(value):
    try:
        isoparse(value)
    except ValueError:
        return False


#  schema builder
class QuerySchemaBuilder:
    """class generating serialization schema from resource parameters"""

    FIELDS_TYPES = {'string': fields.String,
                    'integer': fields.Integer,
                    'float': fields.Float,
                    'bbox': fields.String,
                    'wktgeom': fields.String,
                    'datetime': fields.String,
                    'option': fields.String}

    @staticmethod
    def build_schema(parameters, resource_name):
        resource_fileds = {name: QuerySchemaBuilder._build_field(**properties) for name, properties in
                           parameters.items()}
        if resource_name == 'ccsi':
            schema = type('Schema', (CCSIQuerySchema,), resource_fileds)
        else:
            schema = type('Schema', (ResourceQuerySchema,), resource_fileds)
        return schema()

    @staticmethod
    def _build_field(typ, required=False, default=None, option=None, missing=None, **ignore):
        field_properties = {}
        if option:
            if isinstance(option, str):
                field_properties.update({'validate': partial(validate_choises, choises=[option])})
            else:
                 field_properties.update({'validate': partial(validate_choises, choises=option)})
        field_properties.update({'required': required})
        if default:
            field_properties.update({'default': default})
        if missing is not None:
            field_properties.update({'missing': missing})
        if typ == 'datetime':
            field_properties.update({'validate': validate_datetime})
            
        return QuerySchemaBuilder.FIELDS_TYPES[typ](**field_properties)


#  schema container
class ResourceSchemasContainer(Container):
    """container for resources schemas"""
    pass
