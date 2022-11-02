import dataclasses
import re
import abc
from typing import Optional, Type

import flask_wtf
from flask import current_app
from jinja2 import Environment
from wtforms import Form, fields, validators
from flask_babel import lazy_gettext as lg

from notifico.util import irc
from notifico.services.messages import MessageService


@dataclasses.dataclass
class StructuredMessage:
    """
    A structured message enables sending messages to outgoing services that
    contains more information than just a plain string. It's useful to enable
    richer service on platforms that support it, like Discord and Slack.

    .. note::

        Our original supported platform was IRC, which supports nothing more
        than simple string messages.
    """
    legacy_message: str


class HookService(abc.ABC):
    """
    The base type for any `Service`.
    """
    #: Alias to `notifico.util.irc.colors`
    colors = irc.mirc_colors()

    SERVICE_NAME = None
    SERVICE_ID = None

    @classmethod
    def description(cls) -> str:
        """
        A description of this service as an HTML string.
        """
        return ''

    @staticmethod
    def env() -> Environment:
        """
        Returns a Jinja2 `Environment` for template rendering.
        """
        raise NotImplementedError()

    @classmethod
    def shorten(cls, url: str) -> str:
        """
        If possible, return a shorter version of `url` shortened by a 3rd
        party service. Where the service provides its own shortening service,
        prefer it.
        """
        return url

    @classmethod
    def strip_colors(cls, msg: str) -> str:
        """
        Strip mIRC color codes from `msg` and return it.
        """
        return irc.strip_mirc_colors(msg)

    @classmethod
    def form(cls) -> Optional[Type[Form]]:
        """
        Returns a wtforms.Form subclass which is a form of Service options
        to be shown to the user on setup.
        """
        return None

    @classmethod
    def validate(cls, form: flask_wtf.FlaskForm, request):
        """
        Returns `True` if the form passes validation, `False` otherwise.
        Should be subclassed by complex service configurations.
        """
        return form.validate_on_submit()

    @classmethod
    def pack_form(cls, form: Form) -> dict:
        """
        Returns a dictionary of configuration options processed from `form`.
        By default, simply iterates all fields, taking their ``.id`` as the
        key and ``.data`` as value.
        """
        return dict((f.id, f.data) for f in form)

    @classmethod
    def load_form(cls, form: Form, config: dict) -> Optional[Form]:
        """
        Loads a Hook configuration into an existing Form object, returning it.
        """
        if config is None:
            return

        for f in form:
            if f.id in config:
                f.data = config[f.id]

        return form


class IncomingHookService(HookService, abc.ABC):
    @classmethod
    def message(cls, message: str, strip: bool = True):
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
        return current_app.redis  # noqa

    @classmethod
    def _request(cls, user, request, hook, *args, **kwargs):
        combined = []

        ms = MessageService(redis=cls._redis())
        handler = cls.handle_request(user, request, hook)

        if handler is None:
            # It's entirely possible for a message body to be a NOP,
            # so don't do anything at all.
            return

        for message in handler:
            combined.append(message)
            for channel in hook.project.channels:
                ms.send_message(message, channel)

        if hook.project.public:
            ms.log_message('\n'.join(combined), hook.project)

    @classmethod
    @abc.abstractmethod
    def handle_request(cls, user, request, hook):
        """
        Handle an incoming webhook.
        """
        raise NotImplementedError()


class OutgoingHookService(HookService, abc.ABC):
    class WebhookForm(flask_wtf.FlaskForm):
        """
        Base form all webhook configuration forms should subclass.
        """
        webhook_url = fields.URLField(
            lg('Webhook URL'),
            validators=[
                validators.InputRequired()
            ]
        )

    @classmethod
    def form(cls) -> Optional[Type[Form]]:
        return cls.WebhookForm

    @classmethod
    def process_message(cls, message: str | StructuredMessage):
        if isinstance(message, str):
            return cls.handle_message(StructuredMessage(legacy_message=message))
        return cls.handle_message(message)

    @classmethod
    @abc.abstractmethod
    def handle_message(cls, message: StructuredMessage):
        """
        Handle an outgoing message.
        """
        raise NotImplementedError()
