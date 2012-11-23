# -*- coding: utf8 -*-
from notifico.services.service import *
from notifico.services.github import GithubService


_registered_services = {
    GithubService.service_id(): GithubService
}


def registered_services():
    return _registered_services


def service_from_id(service_id):
    return _registered_services.get(service_id, None)
