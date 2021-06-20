import enum
import functools
from typing import Dict, Any
from importlib.metadata import entry_points

from flask import url_for


@functools.cache
def get_providers() -> Dict[int, 'BaseProvider']:
    """
    Returns a cached dictionary of all known Provider plugins, keyed by
    PROVIDER_ID.
    """
    plugins = entry_points()['notifico.providers']
    return {
        p.PROVIDER_ID: p()
        for p in (plugin.load() for plugin in plugins)
    }


class ProviderTypes(enum.Enum):
    #: Type for providers that want a chance to handle incoming webhooks.
    WEBHOOK = 1
    #: Type for providers that want a chance to poll for events.
    POLLING = 2


class BaseProvider:
    """
    A Provider generates payloads for processing and eventual delivery to a
    :class:~`notifico.target.Target`.

    Providers can be triggered by a webhook, or can come from other sources
    such as polling.

    When a webhook is received, available providers are hit one after another
    until `is_our_payload()` returns `True`. This lets us implement "universal"
    webhooks, which are a big win for user experience.
    """
    #: A unique identifier for a Provider implementation.
    PROVIDER_ID: int = None
    #: A unique, human-readable name for this Provider implementation.
    PROVIDER_NAME: str = None
    #: The type of the provider, such as a webhook or a poller.
    PROVIDER_TYPE: ProviderTypes = None
    #: A short description of this provider. Should be a lazy_gettext-wrapped
    #: string.
    PROVIDER_DESCRIPTION: str = None

    #: The minimum period between polling events for polling-type providers.
    #: Note this only guarantees it won't be polled *before* this duration
    #: has passed, it may take longer. Value is in seconds.
    POLLING_PERIOD: int = None

    @classmethod
    def form(cls):
        """
        An optional Form class that will be presented to the user when
        initially configuring and when editing the Provider.
        """

    @classmethod
    def config_from_form(cls, form) -> Dict[int, Any]:
        """
        Pack a configuration form into a dictionary. The dictionary must
        be safe to serialize as JSON.
        """
        return dict((field.id, field.data) for field in form)

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


class WebhookProvider(BaseProvider):
    PROVIDER_TYPE = ProviderTypes.WEBHOOK

    @classmethod
    def external_url(cls, hook) -> str:
        """
        Returns an absolute, externally-accessible URL to trigger the given
        webhook.
        """
        return url_for(
            'webhooks.trigger',
            project=hook.project_id,
            key=hook.key
        )


class PollingProvider(BaseProvider):
    PROVIDER_TYPE = ProviderTypes.POLLING
