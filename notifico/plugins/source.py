__all__ = (
    'SourceForm',
    'SourceTypes',
    'WebhookSource',
    'PollingSource',
    'SourcePlugin'
)
import enum

import flask_wtf
from flask import url_for
from flask_babel import lazy_gettext as _
from wtforms import fields, validators

from notifico.plugins.core import CorePlugin


class SourceForm(flask_wtf.FlaskForm):
    """
    A base form most sources should use for their configuration options.
    """
    description = fields.StringField(
        _('Description'),
        validators=[
            validators.Optional()
        ],
        description=_(
            'Optionally provide a short description to make it easier to'
            ' recall what this source is for. This helps when you have many'
            ' sources on a single project.'
        )
    )


class SourceTypes(enum.Enum):
    #: Type for sources that want a chance to handle incoming webhooks.
    WEBHOOK = 1
    #: Type for sources that want a chance to poll for events.
    POLLING = 2


class SourcePlugin(CorePlugin):
    """
    The base class for Source plugins. Don't directly subclass this (unless
    you _really_ know what you're doing!), instead use :class:`WebhookSource`
    or :class:`PollingSource`.
    """
    #: A unique, human-readable name for this Source implementation.
    SOURCE_NAME: str = None
    #: The type of the source, such as a webhook or a poller.
    SOURCE_TYPE: SourceTypes = None
    #: A short description of this source. Should be a lazy_gettext-wrapped
    #: string.
    SOURCE_DESCRIPTION: str = None

    @classmethod
    def user_form(cls):
        """
        An optional FlaskForm *class* (not an instance!) that will be
        presented to an end user when configuring this plugin.
        """
        return SourceForm


class WebhookSource(SourcePlugin):
    SOURCE_TYPE = SourceTypes.WEBHOOK

    @classmethod
    def external_url(cls, hook) -> str:
        """
        Returns an absolute, externally-accessible URL to trigger the given
        webhook.
        """
        return url_for(
            'webhooks.trigger',
            project=hook.project_id,
            key=hook.key,
            _external=True
        )

    @staticmethod
    def icon() -> str:
        return 'fas fa-link'

    @classmethod
    def pack_payload(cls, source, request) -> bytes:
        """
        Turn the payload of the given request into a `bytes` object that will
        be sent to the background worker for this webhook.

        You do not need to handle headers or other metadata like IPs, this
        will be handled for you. You *do* need to handle the body, URL
        parameters, or anything else of interest to your webhook.
        """
        raise NotImplementedError()

    @classmethod
    def handle_request(cls, request):
        """
        Handle the given incoming request, emitting 0 or more Messages for
        destination channels.
        """
        raise NotImplementedError()


class PollingSource(SourcePlugin):
    SOURCE_TYPE = SourceTypes.POLLING

    @staticmethod
    def icon() -> str:
        return 'fas fa-clock'
