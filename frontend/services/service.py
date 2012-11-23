# -*- coding: utf8 -*-
__all__ = ('Service',)
import json

import redis

from frontend import app


class Service(object):
    COMMIT = 'commit'
    RAW = 'raw'
    ISSUE = 'issue'
    WIKI = 'wiki'

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
            r.publish(
                'message',
                json.dumps(message)
            )
