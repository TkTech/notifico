from flask import (
    Blueprint,
    render_template,
    g,
    abort,
    request,
    url_for
)

from sqlalchemy import func

from notifico.models import User, Channel, Project

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


@public.route('/s/channels/<network>', defaults={'page': 1})
@public.route('/s/channels/<network>/<int:page>')
def channels(network, page=1):
    """
    Show all the channels on the given network.
    """
    per_page = min(int(request.args.get('l', 25)), 100)

    q = Channel.query.join(Project).filter(
        Channel.host == network,
        Channel.public == True,
        Project.public == True
    )

    pagination = q.paginate(page, per_page, False)

    return render_template('channels.html',
        per_page=per_page,
        network=network,
        pagination=pagination
    )


@public.route('/s/projects', defaults={'page': 1})
@public.route('/s/projects/<int:page>')
def projects(page=1):
    per_page = min(int(request.args.get('l', 25)), 100)
    sort_by = request.args.get('s', 'created')

    q = Project.query.filter_by(public=True).order_by(False)
    q = q.order_by({
        'created': Project.created.desc(),
        'messages': Project.message_count.desc()
    }.get(sort_by, Project.created.desc()))

    pagination = q.paginate(page, per_page, False)

    return render_template('projects.html',
        pagination=pagination,
        per_page=per_page
    )


@public.route('/s/users/')
@public.route('/s/users/<int:page>')
def users(page=1):
    q = User.query.order_by(False).order_by(User.joined.desc())

    return render_template('users.html',
        users=q
    )
