import enum
import functools
from typing import Dict, Any
from importlib.metadata import entry_points

import flask_wtf
from flask import url_for
from wtforms import fields, validators
from flask_babel import lazy_gettext as _


@functools.cache
def get_installed_sources() -> Dict[int, 'SourcePlugin']:
    """
    Returns a cached dictionary of all known Source plugins, keyed by
    SOURCE_ID.
    """
    # Adding a way to purge this cache in all processes via a signal would
    # allow us to hot-load new plugin sources without having to restart
    # notifico. Worth looking into.
    plugins = entry_points()['notifico.sources']
    return {
        p.SOURCE_ID: p()
        for p in (plugin.load() for plugin in plugins)
    }


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


class SourcePlugin:
    """
    A SourcePlugin generates payloads for processing and eventual delivery to a
    :class:~`notifico.channel.Channel`.
    """
    #: A unique identifier for a Source implementation.
    SOURCE_ID: int = None
    #: A unique, human-readable name for this Source implementation.
    SOURCE_NAME: str = None
    #: The type of the source, such as a webhook or a poller.
    SOURCE_TYPE: SourceTypes = None
    #: A short description of this source. Should be a lazy_gettext-wrapped
    #: string.
    SOURCE_DESCRIPTION: str = None

    #: The minimum period between polling events for polling-type sources.
    #: Note this only guarantees it won't be polled *before* this duration
    #: has passed, it may take longer. Value is in seconds.
    POLLING_PERIOD: int = None

    @classmethod
    def form(cls):
        """
        An optional Form class that will be presented to the user when
        initially configuring and when editing the Source.
        """

    @classmethod
    def config_from_form(cls, form) -> Dict[int, Any]:
        """
        Pack a configuration form into a dictionary. The dictionary must
        be safe to serialize as JSON.
        """
        return dict(
            (field.id, field.data) for field in form
            if field.id != 'csrf_token'
        )

    @classmethod
    def update_form_with_config(cls, form, config):
        """
        Update the provided form instance using the stored configuration
        in `config`.
        """
        if config is None or not isinstance(config, dict):
            return

        for field in form:
            if field.id in config:
                field.data = config[field.id]

    @staticmethod
    def icon() -> str:
        """The Font-Awesome icon that should be used to identify this
        source, if any is suitable."""
        return 'fas fa-question'


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
