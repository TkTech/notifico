from flask import (
    Blueprint,
    render_template,
    g
)

from sqlalchemy import func

from notifico.models import User, Channel, Project
from notifico.util import irc
from notifico.services.messages import MessageService

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    ms = MessageService(g.redis)

    # Find the 25 most recent messages.
    recent_messages = ms.recent_messages(0, 25)
    for message in recent_messages:
        project = Project.query.get(message['project_id'])
        if project is None or project.owner.id != message['owner_id']:
            # Skip messages whose associated project has been deleted.
            continue

        message['project'] = project
        message['msg'] = irc.to_html(message['msg'])

    # Sum the total number of messages across all projects
    total_messages = g.redis.get('cache_message_count')
    if total_messages is None:
        total_messages = g.db.session.query(
            func.sum(Project.message_count)
        ).scalar()
        g.redis.setex('cache_message_count', 120, total_messages)

    return render_template('landing.html',
        recent_messages=recent_messages,
        total_projects=Project.query.count(),
        total_users=User.query.count(),
        total_messages=total_messages,
        total_channels=Channel.query.count()
    )


@public.route('/s/channels/<network>')
def channels(network):
    q = Channel.query.filter_by(host=network, public=True)

    return render_template('channels.html',
        channels=q,
        network=network
    )


@public.route('/s/users/')
@public.route('/s/users/<int:page>')
def users(page=1):
    q = User.query.order_by(False).order_by(User.joined.desc())

    return render_template('users.html',
        users=q
    )
