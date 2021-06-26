import inspect

from notifico.tasks import celery
from notifico.models.provider import Provider

OPTIONAL_KWARGS = (
    'remote_ip',
    'payload'
)


@celery.task(name='dispatch_webhook')
def dispatch_webhook(provider_id, **kwargs):
    provider = Provider.query.get(provider_id)
    if provider is None:
        # Not sure what we should do here. The provider was deleted in the
        # (hopefully) short time between receiving it and acting on it. There
        # is no longe a Provider object to log to.
        return

    # We only pass some keyword arguments if the handler has them in their
    # signature. We want to minimize overhead of making Providers as much as
    # possible.
    sig = inspect.signature(provider.p.handle_request)
    optionals = {
        k: kwargs.get(k) for k in OPTIONAL_KWARGS if k in sig.parameters
    }

    try:
        provider.p.handle_request(provider, **optionals)
    except Exception:
        # FIXME: Update provider health and log.
        raise
