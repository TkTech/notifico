from flask import Blueprint
from flask_restful import Api, Resource, url_for

from notifico.views.api import api


class UserAPI(Resource):
    def get(self, id: int):
        return {}

api.add_resource(UserAPI, '/user/<int:id>')
