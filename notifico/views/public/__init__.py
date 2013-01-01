from flask import (
    Blueprint,
    render_template,
    g,
    abort
)

from sqlalchemy import func

from notifico.models import User, Channel, Project
from notifico.util import irc
from notifico.services.messages import MessageService

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    """
    Show a landing page giving a short intro blurb to unregistered users
    and very basic metrics such as total users.
    """
    # Sum the total number of messages across all projects, caching
    # it for the next two minutes.
    total_messages = g.redis.get('cache_message_count')
    if total_messages is None:
        total_messages = g.db.session.query(
            func.sum(Project.message_count)
        ).scalar()
        g.redis.setex('cache_message_count', 120, total_messages)

    # Find the 10 latest public projects.
    public_projects = (
        Project.query
        .filter_by(public=True)
        .order_by(False)
        .order_by(Project.created.desc())
        .limit(10)
    )

    # Find the 10 most popular networks.
    popular_networks = (
        g.db.session.query(
            Channel.host, func.count(Channel.channel).label('count')
        )
        .filter_by(public=True)
        .group_by(Channel.host)
        .order_by('-count')
        .limit(10)
    )

    return render_template('landing.html',
        total_projects=Project.query.count(),
        total_users=User.query.count(),
        total_messages=total_messages,
        total_channels=Channel.query.count(),
        public_projects=public_projects,
        popular_networks=popular_networks
    )


@public.route('/s/channels/<network>')
def channels(network):
    q = Channel.query.filter_by(host=network, public=True)
    if not q.count():
        return abort(404)

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
