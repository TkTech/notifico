from flask import (
    Blueprint,
    request,
    render_template,
    abort,
    make_response,
    jsonify
)

from notifico import errors
from notifico.extensions import db
from notifico.models.log import Log, LogContext, LogContextType
from notifico.models.source import SourceInstance
from notifico.plugin import SourceTypes
from notifico.models.project import Project

webhooks = Blueprint('webhooks', __name__)


@webhooks.route('/<int:project>/<key>', methods=['GET', 'POST'])
def trigger(project, key):
    """
    Dispatches incoming webhooks to their respective projects and associated
    source.
    """
    from notifico.tasks import celery

    # Since we don't currently have any sources that issue a completely
    # empty GET request, we handle that case and return a help page. Users
    # keep clicking on the URLs.
    if request.method == 'GET' and not request.args:
        # Currently, this page is very minimal, but it's better than nothing or
        # a cryptic error. We should provide actual help.
        return render_template('errors/this_is_a_webhook.html')

    source = SourceInstance.query.filter(
        SourceInstance.project_id == project,
        SourceInstance.key == key
    ).first()

    # All hooks generate a key, even ones that aren't actually accessible via
    # webhook.
    if source is None or source.impl.SOURCE_TYPE != SourceTypes.WEBHOOK:
        abort(404)

    try:
        packed = source.impl.pack_payload(source, request)
    except Exception as e:
        # Any exception causes a reduction in health score. Then we re-raise
        # for more specific error handlers.
        source.health = SourceInstance.health - 1
        source.project.health = Project.health - 1

        db.session.add(
            Log.error(
                summary=(
                    'An unspecified error occured when processing a webhook.'
                ),
                payload={
                    'request_ip': request.remote_addr
                },
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

        try:
            raise e
        except errors.PayloadNotValidError:
            abort(
                make_response(
                    jsonify({
                        'msg': 'Webhook payload was malformed.'
                    }),
                    400
                )
            )

    task = celery.send_task(
        'dispatch_webhook',
        (source.id,),
        {
            'remote_ip': request.remote_addr,
            'payload': packed
        }
    )

    return make_response(
        jsonify({
            'msg': 'Webhook accepted for processing.',
            'task_id': task.id
        }),
        200
    )
