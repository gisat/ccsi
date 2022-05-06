from marshmallow import Schema, fields, post_load, pre_load, post_dump, EXCLUDE, ValidationError
from marshmallow.validate import OneOf, ContainsOnly
from shapely import wkt, errors
from shapely.geometry import box
from dateutil.parser import isoparse
from ccsi.base import Container, ExcludeSchema, ResourceQuerySchema, CCSIQuerySchema, WekeoQuerySchema, partial
import re
from abc import ABC, abstractmethod
from dateutil.parser import isoparse
from dateutil.rrule import rrule, HOURLY
from datetime import datetime
from dateutil.tz import UTC
from pydantic import BaseModel, Field, validator, Extra
from typing import Union, Optional


# transformation
def identity(self, value):
    return value


def offset(self, value, offset):
    return value + offset


def default(self, value, default):
    return default


def bracket(self, value):
    return f'[{value}]'


def get_mapped_pair(self, value):
    return self.mapping[value]


def utc_time_format(self, value):
    return isoparse(value).strftime("%Y-%m-%dT%H:%M:%S0Z")


def rfc_time_format(self, value):
    return isoparse(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def wekeo_C3S_time_format(self, value):
    return isoparse(value).strftime("%Y,%m,%d,%H:%M")


def time_to_datetime(self, value):
    return isoparse(value)


def wekeo_parameter_form(self, value):
    return {'name': self.name, 'value': value}


def wekeo_multi_parameter_form(self, value):
    if isinstance(value, list):
        return {'name': self.name, 'value': value}
    return {'name': self.name, 'value': [value]}


def wekeo_bbox_form(self, value):
    return {'name': self.name, 'bbox': value}


def wekeo_cams_bbox_form(self, value):
    return {'name': self.name, 'area': value}


def wekeo_time_parameter_form(self, value):
    return {'name': 'position', self.name: value}


def wekeo_time_cams_parameter_form(self, value):
    return {'name': 'date', self.name: value}


def wekeo_time_c3s_parameter_form(self, value):
    names = self.name.split(',')
    times = isoparse(value).strftime("%Y,%m,%d,%H:%M").split(',')
    return [{"name": name, "value": [time]} for name, time in zip(names, times)]


def wekeo_bbox(self, value: str):
    return [float(item) for item in value.split(',')]


def round_list(self, value, precision):
    return [round(v, precision) for v in value]


class TimeParser(ABC):

    def execute(self) -> Union[list, dict]:
        pass


class CamsTimeParser(BaseModel, TimeParser):
    timeStart: datetime
    timeEnd: Optional[datetime] = Field(default=datetime.now())

    def execute(self) -> Union[list, dict]:
        return {'date': f'{self.timeStart.strftime("%Y-%m-%d")}/{self.timeEnd.strftime("%Y-%m-%d")}'}

    @validator('timeStart', pre=True)
    def validate_start(cls, value: str) -> datetime:
        return isoparse(value)

    @validator('timeEnd', pre=True)
    def validate_end(cls, value: str) -> datetime:
        return isoparse(value)



class WekeoCamsTimeParser(TimeParser):

    def __init__(self, query):
        if 'timeStart' in query:
            self.timeStart = isoparse(query['timeStart'])
        if 'timeEnd' in query:
            self.timeEnd = isoparse(query['timeEnd'])
        else:
            self.timeEnd = isoparse(datetime.now().isoformat())
        self.year = set()
        self.month = set()
        self.day = set()
        self.hour = set()

    def parser_datetime_range(self):
        for date in [dt for dt in rrule(HOURLY, dtstart=self.timeStart, until=self.timeEnd)]:
            self.year.add(date.strftime("%Y"))
            self.month.add(date.strftime("%m"))
            self.day.add(date.strftime("%d"))
            self.hour.add(date.strftime("%H:%M"))

    def execute(self):
        self.parser_datetime_range()
        return [self.time_template(name, getattr(self, name)) for name in ['year', 'month', 'day', 'hour']]

    def time_template(self, name:str, value: set):
        return {"name": name, "value": list(value)}


TRANSFORMATION_FUNC = {'identity': identity,
                       'offset': offset,
                       'bracket': bracket,
                       'default': default,
                       'time_to_datetime': time_to_datetime,
                       'utc_time_format': utc_time_format,
                       'rfc_time_format': rfc_time_format,
                       'get_mapped_pair':  get_mapped_pair,
                       'wekeo_parameter_form': wekeo_parameter_form,
                       'wekeo_multi_parameter_form': wekeo_multi_parameter_form,
                       'wekeo_bbox_form': wekeo_bbox_form,
                       'wekeo_cams_bbox_form': wekeo_cams_bbox_form,
                       'wekeo_C3S_time_format': wekeo_C3S_time_format,
                       'wekeo_time_parameter_form': wekeo_time_parameter_form,
                       'wekeo_time_c3s_parameter_form': wekeo_time_c3s_parameter_form,
                       'wekeo_time_cams_parameter_form': wekeo_time_cams_parameter_form,
                       'wekeo_bbox': wekeo_bbox,
                       'round_list': round_list}


# parameters & translator
class Parameter:

    def __init__(self, name: str, typ: str, tranfunc: list, definitions: dict):
        self.name = name
        for item in tranfunc:
            setattr(self, item.__name__, item.__get__(self))
        self.tranfunc = [item.__name__ for item in tranfunc]
        self.typ = typ
        self.definitions = definitions

    def validate(self, value):
        if isinstance(value, str):
            return True
        else:
            raise ValueError(f'{self.__repr__()}: Invalid type of argument {value}, expected {self.__class__.__name__}')

    def transform(self, value):
        parameter_value = value
        for fun in self.tranfunc:
            parameter_value = self.__getattribute__(fun)(parameter_value)
        return {self.name: parameter_value}

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


class Interval(Parameter):
    """class for parametr with options. options is defined as dict. """

    def __init__(self, name, typ, tranfunc, definitions):
        super().__init__(name, typ, tranfunc, definitions)

    def validate(self, value):
        matched = re.match("\d,\d", value)
        if bool(matched):
            return True
        else:
            raise ValueError(f'{self.__repr__()}: Invalid argument {value}, expected one of '
                             f'{", ".join([key for key in self.mapping.keys()])}')

    def transform(self, value):
        if self.validate(value):
            new = self.tranfunc(value)
            return {self.name: new}



PARAM_TYPES = {'string': String,
               'integer': Integer,
               'float': Float,
               'bbox': Bbox,
               'wktgeom': WKTGeom,
               'datetime': DateTime,
               'option': Options,
               'interval': Interval}


class AnyType(fields.Field):
    """Any type """

    def _serialize(self, value, attr, obj, **kwargs):
        return

    def _deserialize(self, value, attr, data, **kwargs):
        return value


class TransFunction(fields.Field):

    def _serialize(self, value, attr, obj, **kwargs):
        return

    def _deserialize(self, value, attr, data, **kwargs):
        if all(item['name'] in TRANSFORMATION_FUNC for item in value):
            fun_sequence = []
            for item in value:
                if item['property'] is None:
                    fun_sequence.append(TRANSFORMATION_FUNC.get(item['name']))
                else:
                    fun_sequence.append(partial(TRANSFORMATION_FUNC.get(item['name']), **item['property']))
            return fun_sequence
        else:
            raise ValidationError(f"Parameter: {data['name']}: "
                                  f"Transformation function specification contain unknown function name")


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


class ResourcesParametersContainer(Container):
    """container for set of resource api parameters"""

    def __int__(self):
        super(ResourcesParametersContainer, self).__int__()

    def create(self, resource_name):
        self.items.update({resource_name: ResourceParameters()})

    def update(self, resource_name, parameters):
        for name, properties in parameters.items():
            self.items[resource_name].update(name, properties)


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
                    'option': fields.String,
                    'interval': fields.String}

    @staticmethod
    def build_schema(parameters, resource_name):
        resource_fileds = {name: QuerySchemaBuilder._build_field(**properties) for name, properties in
                           parameters.items()}
        if resource_name == 'ccsi':
            schema = type('Schema', (CCSIQuerySchema,), resource_fileds)
        elif resource_name.__contains__('wekeo'):
            schema = type('Schema', (WekeoQuerySchema,), resource_fileds)
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
