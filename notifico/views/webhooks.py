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
from notifico.models.log import Log
from notifico.models.source import Source
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

    source = Source.query.filter(
        Source.project_id == project,
        Source.key == key
    ).first()

    # All hooks generate a key, even ones that aren't actually accessible via
    # webhook.
    if source is None or source.source_type != SourceTypes.WEBHOOK:
        abort(404)

    try:
        packed = source.p.pack_payload(source, request)
    except Exception as e:
        # Any exception causes a reduction in health score. Then we re-raise
        # for more specific error handlers.
        source.health = Source.health - 1
        source.project.health = Project.health - 1

        log = Log.error(summary=(
            'An unspecified error occured when processing a webhook.'
        ))

        source.project.logs.append(log)
        source.logs.append(log)

        db.session.add(source)
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
