from flask import (
    Blueprint,
    render_template,
    g
)
from sqlalchemy import func

from notifico.models import Project, User, Channel, Hook

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    """
    Public landing page visible to everyone with summary statistics
    and an intro blurb for unregistered users.
    """
    # Find the 10 most recently created projects.
    new_projects = (
        Project.query.filter_by(public=True)
        .order_by(False)
        .order_by(Project.created.desc())
        .limit(10)
    )

    # Get the total number of messages recieved and cache it in redis
    # for 2 minutes.
    message_count = g.redis.get('cache_message_count')
    if message_count is None:
        message_count = g.db.session.query(
            func.sum(Project.message_count)
        ).scalar()
        g.redis.setex('cache_message_count', 120, message_count)

    channel_count_by_network = Channel.channel_count_by_network()

    return render_template('landing.html',
        Project=Project,
        User=User,
        Channel=Channel,
        channel_count_by_network=channel_count_by_network,
        Hook=Hook,
        new_projects=new_projects,
        message_count=message_count
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
