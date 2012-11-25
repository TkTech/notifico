# -*- coding: utf8 -*-
from notifico.services.service import *
from notifico.services.github import GithubService
from notifico.services.plain import PlainTextService


_registered_services = {
    GithubService.service_id(): GithubService,
    PlainTextService.service_id(): PlainTextService
}


def registered_services():
    return _registered_services


def service_from_id(service_id):
    return _registered_services.get(service_id, None)
