from ccsi.base import Container, ExcludeSchema
from ccsi.resource.parameters import ResourcesParametersContainer, WekeoCamsTimeParser, CamsTimeParser, OndaTimeParser
from ccsi.config import Config

from abc import ABC, abstractmethod
from marshmallow import Schema, fields, post_load, pre_load, post_dump, EXCLUDE, ValidationError
from marshmallow.validate import OneOf, ContainsOnly


class Translator(ABC):

    @abstractmethod
    def translate(self, query: dict):
        pass

    @abstractmethod
    def get_mapped_pairs(self, resource_name):
        pass

    @abstractmethod
    def validate(self, query: dict):
        pass


class BasicTranslator(Translator):
    """ class responsible for translation from ccsi set o api params to resource api params"""

    def __init__(self, resources_parameters: ResourcesParametersContainer):
        self.resources_parameters = resources_parameters

    def translate(self, query: dict, **kwargs):
        """translate from one set of api parameters to another
        :param **kwargs:
        """
        translated_query = {}
        for key, value in query.items():
            parameter = self.resources_parameters.get_parameter(key)
            translated_query.update(parameter.transform(value))
        return translated_query

    def get_mapped_pairs(self, resource_name):
        return self.resources_parameters.get_item(resource_name).get_mapped_pairs()

    def validate(self, query: dict):
        """validate from one set of api parameters to another"""
        for key, value in query.items():
            self.resources_parameters.get_parameter(key).validate(value)


class WekeoTranslator(Translator):
    def __init__(self, resources_parameters: ResourcesParametersContainer):
        self.resources_parameters = resources_parameters
        self.processed_query = {}

    def translate(self, query: dict, **kwargs):
        """translate from one set of api parameters to another
        """

        for key, value in query.items():
            parameter = self.resources_parameters.get_parameter(key)
            if parameter.definitions['target'] == 'query_params':
                getattr(self, parameter.definitions['target'])(parameter.transform(value))
            elif parameter.definitions['target'] is None:
                pass
            else:
                getattr(self, parameter.definitions['target'])(parameter.transform(value)[parameter.name])
        return self.processed_query

    def get_mapped_pairs(self, resource_name):
        return self.resources_parameters.get_item(resource_name).get_mapped_pairs()

    def validate(self, query: dict):
        """validate from one set of api parameters to another"""
        for key, value in query.items():
            self.resources_parameters.get_parameter(key).validate(value)

    def stringInputs(self, parameter):
        if 'stringInputs' not in self.processed_query:
            self.processed_query['stringInputs'] = []
        self.processed_query['stringInputs'].append(parameter)

    def stringChoicesValues(self, parameter):
        if 'stringChoiceValues' not in self.processed_query:
            self.processed_query['stringChoiceValues'] = []
        self.processed_query['stringChoiceValues'].append(parameter)

    def multiStringSelectValues(self, parameter):
        if 'multiStringSelectValues' not in self.processed_query:
            self.processed_query['multiStringSelectValues'] = []
        if isinstance(parameter, list):
            self.processed_query['multiStringSelectValues'] += parameter
        elif isinstance(parameter, dict):
            self.processed_query['multiStringSelectValues'].append(parameter)

    def dateRangeSelectValues(self, parameter):
        if 'dateRangeSelectValues' not in self.processed_query:
            self.processed_query['dateRangeSelectValues'] = [parameter]
        self.processed_query['dateRangeSelectValues'][0].update(parameter)

    def boundingBoxValues(self, parameter):
        if 'boundingBoxValues' not in self.processed_query:
            self.processed_query['boundingBoxValues'] = []
        self.processed_query['boundingBoxValues'].append(parameter)

    def wekeo_dataset_from_string_choice(self, data):
        value, datasetid = data['value'].split(',')
        data['value'] = value
        self.wekeo_dataset_id(datasetid)
        self.stringChoicesValues(data)

    def wekeo_dataset_from_multiStringSelectValues(self, data):
        value, datasetid = data['value'][0].split(',')
        data['value'] = [value]
        self.wekeo_dataset_id(datasetid)
        self.multiStringSelectValues(data)

    def wekeo_dataset_id(self, parameter):
        self.processed_query['datasetId'] = parameter

    def query_params(self, parameter):
        if 'query_params' not in self.processed_query:
            self.processed_query['query_params'] = {}
        self.processed_query['query_params'].update(parameter)


class WekeoC3STranslator(Translator):
    def __init__(self, resources_parameters: ResourcesParametersContainer):
        self.resources_parameters = resources_parameters

    def translate(self, query: dict, **kwargs):
        """translate from one set of api parameters to another
        """
        self.time_set = WekeoCamsTimeParser(query)
        self.processed_query = {}

        for key, value in query.items():
            parameter = self.resources_parameters.get_parameter(key)
            if parameter.definitions['target'] == 'query_params':
                getattr(self, parameter.definitions['target'])(parameter.transform(value))
            elif parameter.definitions['target'] is None:
                pass
            else:
                getattr(self, parameter.definitions['target'])(parameter.transform(value)[parameter.name])

        return self.processed_query

    def get_mapped_pairs(self, resource_name):
        return self.resources_parameters.get_item(resource_name).get_mapped_pairs()

    def validate(self, query: dict):
        """validate from one set of api parameters to another"""
        for key, value in query.items():
            self.resources_parameters.get_parameter(key).validate(value)

    def stringInputs(self, parameter, **ignore):
        if 'stringInputs' not in self.processed_query:
            self.processed_query['stringInputs'] = []
        self.processed_query['stringInputs'].append(parameter)

    def stringChoicesValues(self, parameter, **ignore):
        if 'stringChoiceValues' not in self.processed_query:
            self.processed_query['stringChoiceValues'] = []
        self.processed_query['stringChoiceValues'].append(parameter)

    def multiStringSelectValues(self, parameter, **ignore):
        if 'multiStringSelectValues' not in self.processed_query:
            self.processed_query['multiStringSelectValues'] = []
        if isinstance(parameter, list):
            self.processed_query['multiStringSelectValues'] += parameter
        elif isinstance(parameter, dict):
            self.processed_query['multiStringSelectValues'].append(parameter)

    def dateRangeSelectValues(self, parameter, **ignore):
        if 'dateRangeSelectValues' not in self.processed_query:
            self.processed_query['dateRangeSelectValues'] = [parameter]
        self.processed_query['dateRangeSelectValues'][0].update(parameter)

    def boundingBoxValues(self, parameter, **ignore):
        if 'boundingBoxValues' not in self.processed_query:
            self.processed_query['boundingBoxValues'] = []
        self.processed_query['boundingBoxValues'].append(parameter)

    def wekeo_dataset_from_string_choice(self, data, **ignore):
        value, datasetid = data['value'].split(',')
        data['value'] = value
        self.wekeo_dataset_id(datasetid)
        self.stringChoicesValues(data)

    def wekeo_dataset_from_multiStringSelectValues(self, data, **ignore):
        value, datasetid = data['value'][0].split(',')
        data['value'] = [value]
        self.wekeo_dataset_id(datasetid)
        self.multiStringSelectValues(data)

    def wekeo_dataset_id(self, parameter, **ignore):
        self.processed_query['datasetId'] = parameter

    def wekeoC3Stime(self, data):
        if self.time_set:
            self.multiStringSelectValues(self.time_set.execute())
            self.time_set = None

    def query_params(self, parameter, **ignore):
        if 'query_params' not in self.processed_query:
            self.processed_query['query_params'] = {}
        self.processed_query['query_params'].update(parameter)


class CamsEAC4Translator(Translator):
    def __init__(self, resources_parameters: ResourcesParametersContainer):
        self.resources_parameters = resources_parameters
        self.processed_query = {}
        self.time_set = None

    def translate(self, query: dict, **kwargs):
        """translate from one set of api parameters to another
        """
        self.processed_query = {}
        self.time_set = CamsTimeParser.parse_obj(query)

        for key, value in query.items():
            parameter = self.resources_parameters.get_parameter(key)
            if parameter.definitions['target'] == 'query_params':
                pass
            elif not parameter.definitions.get('target'):
                parameter = self.resources_parameters.get_parameter(key)
                self.processed_query.update(parameter.transform(value))
            else:
                getattr(self, parameter.definitions['target'])(parameter.transform(value)[parameter.name])

        return self.processed_query

    def get_mapped_pairs(self, resource_name):
        return self.resources_parameters.get_item(resource_name).get_mapped_pairs()

    def validate(self, query: dict):
        """validate from one set of api parameters to another"""
        for key, value in query.items():
            self.resources_parameters.get_parameter(key).validate(value)

    def wekeo_dataset_id(self, parameter, **ignore):
        self.processed_query['datasetId'] = parameter

    def time(self, *args, **ignore):
        if self.time_set:
            self.processed_query.update(self.time_set.execute())

    def query_params(self, parameter, **ignore):
        if 'query_params' not in self.processed_query:
            self.processed_query['query_params'] = {}
        self.processed_query['query_params'].update(parameter)


class OndaTranslator(Translator):
    def __init__(self, resources_parameters: ResourcesParametersContainer):
        self.resources_parameters = resources_parameters
        self.processed_query = {}
        self.time_set = None

    def translate(self, query: dict, **kwargs):
        """translate from one set of api parameters to another
        """
        self.processed_query = {}
        self.time_set = OndaTimeParser.parse_obj(query)

        for key, value in query.items():
            parameter = self.resources_parameters.get_parameter(key)

            if not parameter.definitions['target']:
                self.processed_query.update(parameter.transform(value))
            else:
                getattr(self, parameter.definitions['target'])(parameter.name, parameter.transform(value)[parameter.name])

        return self.processed_query

    def get_mapped_pairs(self, resource_name):
        return self.resources_parameters.get_item(resource_name).get_mapped_pairs()

    def validate(self, query: dict):
        """validate from one set of api parameters to another"""
        for key, value in query.items():
            self.resources_parameters.get_parameter(key).validate(value)

    def time(self, *args, **ignore):
        if not self.processed_query.get('$search'):
            self.processed_query.update({'$search': {}})
        if self.time_set:
            self.processed_query.get('$search').update(self.time_set.execute())

    def query_param(self, name, value, **ignore):
        self.processed_query.update({f'${name}': value})

    def search(self, name, value, **ignore):
        if not self.processed_query.get('$search'):
            self.processed_query.update({'$search': {}})
        self.processed_query.get('$search').update({name: value})



class TranslatorSchema(ExcludeSchema):
    TYPES = {'basic': BasicTranslator,
             'wekeo': WekeoTranslator,
             'wekeoC3S': WekeoC3STranslator,
             'cams_eac4': CamsEAC4Translator,
             'onda': OndaTranslator}
    typ = fields.Str(required=True, validate=OneOf(TYPES))

    @post_load(pass_original=True)
    def make_parameter(self, data, original_data, **kwargs):
        return self.TYPES.get(data['typ'])