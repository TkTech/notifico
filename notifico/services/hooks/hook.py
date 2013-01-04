# -*- coding: utf8 -*-
__all__ = ('HookService',)
import re

import redis
from jinja2 import Environment, PackageLoader

from notifico import app
from notifico.util import irc
from notifico.services import Service
from notifico.services.messages import MessageService


class HookService(object):
    """
    The base type for any `Service`.
    """
    __metaclass__ = Service
    #: Alias to `notifico.util.irc.colors`
    colors = irc.mirc_colors()

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
            loader=PackageLoader('notifico.services.hooks', 'templates')
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
        return irc.strip_mirc_colors(msg)

    @classmethod
    def message(cls, message, strip=True):
        # Optionally strip mIRC color codes.
        message = cls.strip_colors(message) if strip else message
        # Strip newlines and other whitespace.
        message = re.sub(r'\s+', ' ', message)
        return message

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
    def _request(cls, user, request, hook, *args, **kwargs):
        combined = []

        ms = MessageService(redis=cls._redis())
        handler = cls.handle_request(user, request, hook, *args, **kwargs)
        for message in handler:
            combined.append(message)
            for channel in hook.project.channels:
                ms.send_message(message, channel)

        if hook.project.public:
            ms.log_message('\n'.join(combined), hook.project)

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
        Should be subclassed by complex service configurations.
        """
        return form.validate_on_submit()

    @classmethod
    def pack_form(cls, form):
        """
        Returns a dictionary of configuration options processed from `form`.
        By default, simply iterates all fields, taking their ``.id`` as the
        key and ``.data`` as value.
        """
        return dict((f.id, f.data) for f in form)

    @classmethod
    def load_form(cls, form, config):
        """
        Loads a Hook configuration into an existing Form object, returning it.
        """
        if config is None:
            return

        for f in form:
            if f.id in config:
                f.data = config[f.id]

        return form

    @classmethod
    def absolute_url(cls, hook):
        """
        Returns an absolute URL used as this hooks endpoint if it does
        not use the standard hook-recieve endpoint.
        """
        raise NotImplementedError()
