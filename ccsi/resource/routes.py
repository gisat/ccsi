from flask import Response, request, abort, render_template, make_response, Blueprint, jsonify
from flask_restful import Resource, Api, reqparse
from ccsi.storage import storage
from ccsi.base import validate_regpars, ExcludeSchema
from marshmallow import fields
from flasgger import swag_from

api_resource = Blueprint('api_resource', __name__)
api = Api(api_resource)

parser = reqparse.RequestParser()
parser.add_argument('query', type=dict, help='query parameters', location='json')
parser.add_argument('resource_name', type=str, help='Name of resource as string', location='json')
parser.add_argument('parameters', type=dict, help='Resource parameters definitions', location='json')


class RoutesParams(ExcludeSchema):
    query = fields.Dict()
    resource_name = fields.String()
    parameters = fields.Dict()


# parameters
class Parameters(Resource):
    """endponint to manipulate with resources parameters  sets"""
    def __init__(self, **kwargs):
        self.parameters = kwargs['parameters']

    def exist(self, resource_name):
        if resource_name in storage.resources_parameters.get_item_list()['items']:
            return True

    def make_operation(self, resource_name, operation, msg):
        try:
            self.parameters.__getattribute__(operation)(resource_name)
        except Exception as e:
            return {"message": f"Failed to {msg} Resource Parameters container for {resource_name}"}, 400
        return {"message": f" Parameters container {resource_name} successfully {msg}"}, 201

    def get(self):
        """
        Return registered resources parameters set as list of resources names
        ---
        tags:
          - Parameters
        produces:
          - application/json
        responses:
          200:
            description: List of resources, which parameters sets are registered
            examples:
            items: [ccsi]
        """
        return self.parameters.get_item_list(), 200

    def post(self):
        """
        Register resource parameters set container
        ---
        tags:
          - Parameters
        produces:
          - application/json
        parameters:
          - in: body
            description: Name of resource
            name: resource_name
            type: string
            required: true
            schema:
              type: string
              items:
                resource_name : name
        responses:
          '200':
            description: Container for resource parameters for given resource is created
        """
        resource_name = parser.parse_args()['resource_name']
        if self.exist(resource_name):
            return {"message": f"Failed to create Resource Parameters container for resource {resource_name}."
                               f"Resource exist."}, 400
        return self.make_operation(resource_name, 'create', 'create')

    def delete(self):
        """
        Delete resource parameters set container
        ---
        tags:
          - Parameters
        produces:
          - application/json
        parameters:
          - in: body
            description: Name of resource
            name: resource_name
            type: string
            required: true
            schema:
              type: string
              items:
                resource_name : name
        responses:
          200:
            description: Container for resource parameters for given resource was deleted
          400:
            description: Unknown resource name
        """
        resource_name = parser.parse_args()['resource_name']
        if self.exist(resource_name):
            return self.make_operation(resource_name, 'delete', 'delete')
        else:
            return {"message": f"Unknown resource  {resource_name}"}, 400


api.add_resource(Parameters, '/resources/parameters', resource_class_kwargs={'parameters': storage.resources_parameters})


class ParametersResource(Resource):
    """endpoint to manipulate with resources parameters """

    def __init__(self, **kwargs):
        self.parameters = kwargs['parameters']

    def exist(self, resource_name):
        if resource_name in storage.resources_parameters.get_item_list()['items']:
            return True
        else:
            abort(400, f'Unknown resource name {resource_name}')

    def exist_param(self, resource_name, parameter_name):
        if parameter_name in storage.resources_parameters.get_item(resource_name).__dict__:
            return True

    def make_operation(self, resource_name, properties, parameter_name, operation, msg):
        try:
            self.parameters.get_item(resource_name).__getattribute__(operation)(parameter_name, properties)
        except Exception as e:
            return {"message": f"Failed {msg} parameter {parameter_name} in resource {resource_name}. {e}"}, 400

    def get(self, resource_name):
        """
        Return  parameters set definitions for registered resource
        ---
        tags:
          - ParametersResource
        produces:
          - application/json
        parameters:
          - in: path
            description: Name of resource
            name: resource_name
            type: string
            required: true
            schema:
              type: string
        responses:
          200:
            description: List of resources, which parameters sets are registered
        """
        if self.exist(resource_name):
            return {"parameters": self.parameters.get_item(resource_name).get()}, 200

    def post(self, resource_name):
        """
        Create parameters set definitions stored in resource parameters container for given resource
        ---
        tags:
          - ParametersResource
        produces:
          - application/json
        parameters:
          - in: path
            description: Name of resource
            name: resource_name
            type: string
            required: true
            schema:
              type: string
          - in: body
            name: parameters



        responses:
          200:
            description: List of resources, which parameters sets are registered
        """
        parameters = validate_regpars(RoutesParams, 'parameters', parser.parse_args())
        if self.exist(resource_name):
            for parameter_name, properties in parameters.items():
                if not self.exist_param(resource_name, parameter_name):
                    self.make_operation(resource_name, properties, parameter_name, 'update', msg='to create')
                else:
                    abort(400, f'Failed to create parameter {parameter_name} for resource {resource_name}.Parameter '
                               f'already exist. Use PUT instead of.')
            return {"message": self.parameters.get_item(resource_name).get()}, 201

    def put(self, resource_name):
        parameters = validate_regpars(RoutesParams, 'parameters', parser.parse_args())
        if self.exist(resource_name):
            for parameter_name, properties in parameters.items():
                if self.exist_param(resource_name, parameter_name):
                    self.make_operation(resource_name, properties, parameter_name, 'update', msg='to update')
                else:
                    abort(400, f'Resource {resource_name} has not parameter {parameter_name}')
            return {"message": f"{self.parameters.get_item(resource_name).get()}"}, 201

    def delete(self, resource_name):
        parameters = validate_regpars(RoutesParams, 'parameters', parser.parse_args())
        if self.exist(resource_name):
            for parameter_name, properties in parameters.items():
                if self.exist_param(resource_name, parameter_name):
                    self.make_operation(self, resource_name, properties, parameter_name, 'delete', msg='to delete')

            return {"message": f"{self.parameters.get_item(resource_name).get()}"}, 201


api.add_resource(ParametersResource, '/resources/parameters/<string:resource_name>',
                 resource_class_kwargs={'parameters': storage.resources_parameters})


# translator
class ResourceTranslator(Resource):

    def __init__(self, **kwargs):
        self.translator = kwargs['translator']

    def exist(self, resource_name):
        if resource_name in storage.resources_parameters.get_item_list()['items']:
            return True
        else:
            abort(400, f'Unknown resource name {resource_name}')

    def get(self, resource_name):
        """return mapped pairs"""
        if self.exist(resource_name):
            return self.translator.get_mapped_pairs(resource_name), 200

    def post(self, resource_name):
        """translate the guery from ccsi api to resource api"""
        if self.exist(resource_name):
            query = validate_regpars(RoutesParams, 'query', parser.parse_args())
            try:
                response = self.translator.translate(resource_name, )
            except Exception as e:
                return abort(400, e)
            return response, 200


api.add_resource(ResourceTranslator, '/resources/translator/<string:resource_name>',
                 resource_class_kwargs={'translator': storage.translator})

class Schemas(Resource):
    """endponint to manipulate with resources parameters  sets"""
    def __init__(self, **kwargs):
        self.schemas = kwargs['parameters']

    def get(self):
        """return list of registered resources translations """
        return self.schemas.get_item_list(), 200


api.add_resource(Schemas, '/resources/schemas', resource_class_kwargs={'parameters': storage.resource_schemas})
