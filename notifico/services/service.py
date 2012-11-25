# -*- coding: utf8 -*-
__all__ = ('Service',)
import json

import redis
from jinja2 import Environment, PackageLoader

from notifico import app


class Service(object):
    COMMIT = 'commit'
    RAW = 'raw'
    ISSUE = 'issue'
    WIKI = 'wiki'

    COLORS = dict(
        RESET='\x03',
        WHITE='\x03' + '00',
        BLACK='\x03' + '01',
        BLUE='\x03' + '02',
        GREEN='\x03' + '03',
        RED='\x03' + '04',
        BROWN='\x03' + '05',
        PURPLE='\x03' + '06',
        ORANGE='\x03' + '07',
        YELLOW='\x03' + '08',
        LIGHT_GREEN='\x03' + '09',
        TEAL='\x03' + '10',
        LIGHT_CYAN='\x03' + '11',
        LIGHT_BLUE='\x03' + '12',
        PINK='\x03' + '13'
    )

    @staticmethod
    def service_id():
        """
        A unique numeric identifier for this service.
        """
        raise NotImplementedError()

    @staticmethod
    def service_name():
        """
        A unique, human-readable name for this service.
        """
        raise NotImplementedError()

    @staticmethod
    def service_url():
        """
        The URL of the service provider, if one exists.
        """
        raise NotImplementedError()

    @staticmethod
    def service_description():
        """
        A description of this service.
        """
        raise NotImplementedError()

    @staticmethod
    def service_form():
        """
        If the service requires any complex configuration, it should implement
        this method and return a wtforms `Form` object.
        """
        return None

    @staticmethod
    def handle_request(user, request, hook):
        """
        Called on each HTTP request to extract and emit messages.
        """
        raise NotImplementedError()

    @classmethod
    def _request(cls, user, request, hook):
        """
        Called on each HTTP request.
        """
        r = redis.StrictRedis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=app.config['REDIS_DB']
        )
        for message in cls.handle_request(user, request, hook):
            for channel in hook.project.channels:
                message['channel'] = dict(
                    host=channel.host,
                    port=channel.port,
                    ssl=channel.ssl,
                    channel=channel.channel
                )
                r.publish(
                    'message',
                    json.dumps(message)
                )

    @classmethod
    def env(cls):
        """
        Returns a Jinja2 `Environment` for template rendering.
        """
        return Environment(
            loader=PackageLoader('notifico.services', 'templates')
        )
