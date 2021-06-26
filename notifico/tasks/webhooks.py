import inspect

from notifico import db, errors
from notifico.tasks import celery
from notifico.models.log import Log
from notifico.models.project import Project
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
    except Exception as e:
        provider.health = Provider.health - 1
        provider.project.health = Project.health - 1

        try:
            raise e
        except errors.ProviderError as ee:
            msg = str(ee)
            payload = ee.payload or {}
        else:
            msg = 'An unspecified error occured when processing a webhook.'
            payload = {}

        log = Log.error(summary=msg, payload=payload)

        provider.project.logs.append(log)
        provider.logs.append(log)

        db.session.add(provider)
        db.session.commit()

        raise
