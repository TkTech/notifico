import enum
import inspect
import functools
from typing import Dict, Any
from importlib.metadata import entry_points


@functools.cache
def get_providers() -> Dict[int, 'Provider']:
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
    #: Type for providers that may be polling or evented, but will handle it
    #: Themselves.
    SELF_GENERATED = 3


class Provider:
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

    #: The minimum period between polling events for polling-type providers.
    #: Note this only guarantees it won't be polled *before* this duration
    #: has passed, it may take longer. Value is in seconds.
    POLLING_PERIOD: int = None

    @classmethod
    def description(cls, locale: str = 'en_US') -> str:
        """
        A description of this provider as an HTML string.
        """
        raise NotImplementedError()

    @classmethod
    def form(cls) -> dict:
        """
        Returns a form layout, which will be used to generate a wtforms
        Form object.
        """
        raise NotImplementedError()

    @classmethod
    def load_config(cls, config: Dict[str, Any]):
        """
        Deserialize the provider's configuration.
        """
        raise NotImplementedError()

    @classmethod
    def store_config(cls) -> Dict[str, Any]:
        """
        Serialize the provider's configuration.
        """
        raise NotImplementedError()


class WebhookProvider(Provider):
    PROVIDER_TYPE = ProviderTypes.WEBHOOK

    @classmethod
    def dispatch_incoming_webhook(cls, request):
        # Guess which Provider should be responding to this request.
        for provider_id, provider in get_providers().items():
            sig = inspect.signature(provider.is_our_webhook)

            kwargs = {}
            if 'request' in sig.parameters:
                kwargs['request'] = request

            if provider.is_our_webhook(**kwargs):
                break

        # TODO: What do we do when no provider matches? Log it on the project,
        # at least.

    @classmethod
    def is_our_webhook(cls, json: Dict[str, Any], request) -> bool:
        """
        Attempt to identify if we are the correct handler for the given
        request.

        Both the `json` and the `request` arguments are optional. For
        performance, don't include them unless you need them.

        This function is used to guess the correct provider for universal
        webhooks.
        """
        raise NotImplementedError()
