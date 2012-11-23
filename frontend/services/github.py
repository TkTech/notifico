# -*- coding: utf8 -*-
from frontend.services.service import Service


class GithubService(Service):
    @staticmethod
    def service_id():
        return 10

    @staticmethod
    def service_name():
        return 'Github'

    @staticmethod
    def service_url():
        return 'http://github.com'
