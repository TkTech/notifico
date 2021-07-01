import inspect

from notifico import errors
from notifico.tasks import celery
from notifico.extensions import db
from notifico.models.log import Log, LogContext, LogContextType
from notifico.models.project import Project
from notifico.models.source import SourceInstance

OPTIONAL_KWARGS = (
    'remote_ip',
    'payload'
)


@celery.task(name='dispatch_webhook')
def dispatch_webhook(source_id, **kwargs):
    source = SourceInstance.query.get(source_id)
    if source is None:
        # Not sure what we should do here. The source was deleted in the
        # (hopefully) short time between receiving it and acting on it. There
        # is no longe a Source object to log to.
        return

    # We only pass some keyword arguments if the handler has them in their
    # signature. We want to minimize overhead of making Sources as much as
    # possible.
    sig = inspect.signature(source.impl.handle_request)
    optionals = {
        k: kwargs.get(k) for k in OPTIONAL_KWARGS if k in sig.parameters
    }

    try:
        source.impl.handle_request(source, **optionals)
    except Exception as e:
        source.health = SourceInstance.health - 1
        source.project.health = Project.health - 1

        try:
            raise e
        except errors.SourceError as ee:
            msg = str(ee)
            payload = ee.payload or {}
        else:
            msg = 'An unspecified error occured when processing a webhook.'
            payload = {}

        db.session.add(
            Log.error(
                summary=msg,
                payload=payload,
                related=[
                    LogContext(
                        context_type=LogContextType.SOURCE_IMPL,
                        context_id=source.source_id
                    ),
                    LogContext(
                        context_type=LogContextType.SOURCE_INST,
                        context_id=source.id
                    ),
                    LogContext(
                        context_type=LogContextType.PROJECT,
                        context_id=source.project.id
                    ),
                    LogContext(
                        context_type=LogContextType.USER,
                        context_id=source.project.owner.id
                    )
                ]
            )
        )

        db.session.commit()

        raise
