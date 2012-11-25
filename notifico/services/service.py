# -*- coding: utf8 -*-
__all__ = ('Service',)
import re
import json

import redis
from jinja2 import Environment, PackageLoader

from notifico import app


_STRIP_R = re.compile('\x03(?:\d{1,2}(?:,\d{1,2})?)?', re.UNICODE)


class Service(object):
    """
    The base type for any `Service`.
    """
    #: Common mIRC color codes.
    colors = dict(
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

    SERVICE_NAME = None
    SERVICE_ID = None

    @classmethod
    def description(cls):
        """
        A description of this service as a HTML string.
        """
        return ''

    @classmethod
    def env(cls):
        """
        Returns a Jinja2 `Environment` for template rendering.
        """
        return Environment(
            loader=PackageLoader('notifico.services', 'templates')
        )

    @classmethod
    def shorten(cls, url):
        """
        If possible, return a shorter version of `url` shortened by a 3rd
        party service. Where the service provides its own shortening service,
        prefer it.
        """
        return url

    @classmethod
    def strip_colors(cls, msg):
        """
        Strip mIRC color codes from `msg` and return it.
        """
        return _STRIP_R.sub('', msg)

    @classmethod
    def message(cls, message, type_='commit', strip=True):
        """
        Build and return the message template.
        """
        if strip:
            message = cls.strip_colors(message)

        return dict(
            type='message',
            payload=dict(
                msg=message,
                type=type_
            )
        )

    @classmethod
    def _redis(cls):
        """
        Returns a Redis connection instance.
        """
        return redis.StrictRedis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            db=app.config['REDIS_DB']
        )

    @classmethod
    def _request(cls, user, request, hook):
        r = cls._redis()
        for message in cls.handle_request(user, request, hook):
            # Add the destination information to each message before
            # sending...
            for channel in hook.project.channels:
                message['channel'] = dict(
                    channel=channel.channel,
                    host=channel.host,
                    port=channel.port,
                    ssl=channel.ssl
                )
                # ... and send it on its way.
                r.publish(message['type'], json.dumps(message))

    @classmethod
    def form(cls):
        """
        Returns a wtforms.Form subclass which is a form of Service options
        to be shown to the user on setup.
        """
        return None

    @classmethod
    def validate(cls, form, request):
        """
        Returns `True` if the form passes validation, `False` otherwise.
        """
        raise NotImplementedError()

    @classmethod
    def form_to_config(cls, form):
        """
        Returns a dictionary of configuration options.
        """
        raise NotImplementedError()
