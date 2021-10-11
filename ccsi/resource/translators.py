from ccsi.base import Container, ExcludeSchema
from ccsi.resource.parameters import ResourcesParametersContainer
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

    def translate(self, query: dict, **kwargs):
        """translate from one set of api parameters to another
        """
        self.processed_query = {}
        for key, value in query.items():
            parameter = self.resources_parameters.get_parameter(key)
            if parameter.definitions['target'] == 'query_params':
                getattr(self, parameter.definitions['target'])(parameter.transform(value))
            else:
                getattr(self, parameter.definitions['target'])(parameter.transform(value)[parameter.name])
        return self.processed_query

    def get_mapped_pairs(self, resource_name):
        return self.resources_parameters.get_item(resource_name).get_mapped_pairs()

    def validate(self, query: dict):
        """validate from one set of api parameters to another"""
        for key, value in query.items():
            self.resources_parameters.get_parameter(key).validate(value)

    def stringChoicesValues(self, parameter):
        if 'stringChoicesValues' not in self.processed_query:
            self.processed_query['stringChoicesValues'] = []
        self.processed_query['stringChoicesValues'].append(parameter)

    def dateRangeSelectValues(self, parameter):
        if 'dateRangeSelectValues' not in self.processed_query:
            self.processed_query['dateRangeSelectValues'] = [parameter]
        self.processed_query['dateRangeSelectValues'][0].update(parameter)

    def boundingBoxValues(self, parameter):
        if 'boundingBoxValues' not in self.processed_query:
            self.processed_query['boundingBoxValues'] = []
        self.processed_query['boundingBoxValues'].append(parameter)

    def wekeo_dataset_id(self, parameter):
        # self.processed_dataset = [dataset for dataset in self.processed_dataset if dataset.__contains__(parameter)]
        self.processed_query['datasetId'] = parameter

    def query_params(self, parameter):
        if 'query_params' not in self.processed_query:
            self.processed_query['query_params'] = {}
        self.processed_query['query_params'].update(parameter)


class TranslatorSchema(ExcludeSchema):
    TYPES = {'basic': BasicTranslator,
             'wekeo': WekeoTranslator}
    typ = fields.Str(required=True, validate=OneOf(TYPES))

    @post_load(pass_original=True)
    def make_parameter(self, data, original_data, **kwargs):
        return self.TYPES.get(data['typ'])