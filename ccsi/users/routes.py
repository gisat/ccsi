from flask import Response, request, abort, render_template, make_response, Blueprint, jsonify
from flask_restful import Resource, Api, reqparse
from ccsi.storage import storage
from ccsi.base import validate_regpars, ExcludeSchema
from ccsi.models import User
from ccsi import db, auth
from marshmallow import fields
from flasgger import swag_from

api_user = Blueprint('api_user', __name__)
api = Api(api_user)

parser = reqparse.RequestParser()
parser.add_argument('username', type=str, help='User name', location='json')
parser.add_argument('email', type=str, help='User email', location='json')
parser.add_argument('password', type=str, help='password', location='json')


class Users(Resource):

    def get(self):
        return jsonify([user.username for user in User.query.all()])

    @auth.login_required
    def post(self):
        """
        Register new user
        ---
        tags:
          - Parameters
        produces:
          - application/json
        parameters:
          - in: body
            description: User name
            name: username
            type: string
            required: true
            schema:
              type: string
              items:
                username : username
        responses:
          '200':
            description: Container for resource parameters for given resource is created
        """
        username = parser.parse_args()['username']
        email = parser.parse_args()['email']
        password = parser.parse_args()['password']
        if username is None or password is None or email is None:
            abort(400, {'message': 'Username,password or email is missing'})  # missing arguments
        if User.query.filter_by(username=username).first() is not None:
            abort(400, {'message': 'Username is used'})  # existing user
        if User.query.filter_by(email=email).first() is not None:
            abort(400, {'message': 'Email address is used'})  # existing user
        user = User(username=username, email=email)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'username': user.username}), 201

    @auth.login_required
    def delete(self):
        username = parser.parse_args()['username']
        if User.query.filter_by(username=username).first() is None:
            abort(400, {'message': f'Username {username} not found'})  # existing user
        user = User.query.filter_by(username=username).first()
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': f'{username} deleted'}), 200



api.add_resource(Users, '/users')



