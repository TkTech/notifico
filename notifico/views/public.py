from datetime import datetime, timezone
from typing import Optional

from flask import (
    Blueprint,
    render_template,
    g,
    request, abort, url_for
)
from flask_sqlalchemy import Pagination
from sqlalchemy import func, text

from notifico.service import available_services
from notifico.services import stats
from notifico.models import User, Channel, Project
from notifico.database import db_session

public = Blueprint('public', __name__, template_folder='templates')


@public.route('/')
def landing():
    """
    Show a landing page giving a short intro blurb to unregistered users
    and very basic metrics such as total users.
    """
    # Find the 10 latest public projects.
    new_projects = (
        Project.visible(Project.query, user=g.user)
        .order_by(False)
        .order_by(Project.created.desc())
        .limit(10)
    )

    return render_template(
        'public/landing.html',
        new_projects=new_projects,
        top_networks=stats.top_networks(limit=10),
        total_networks=stats.total_networks(),
        total_users=stats.total_users(),
        total_messages=stats.total_messages()
    )


@public.route('/s/networks/')
def networks():
    per_page = min(int(request.args.get('l', 25)), 100)
    page = max(int(request.args.get('page', 1)), 1)

    q = (
        Channel.visible(db_session.query(
            Channel.host,
            func.count(func.distinct(Channel.channel)).label('di_count'),
            func.count(Channel.channel).label('count')
        ), user=g.user)
        .group_by(Channel.host)
        .order_by(text('di_count desc'))
    )
    total = q.count()
    items = q.limit(per_page).offset((page - 1) * per_page).all()
    pagination = Pagination(q, page, per_page, total, items)

    return render_template(
        'public/networks.html',
        pagination=pagination,
        per_page=per_page
    )


@public.route('/s/networks/<network>/')
def network(network):
    per_page = min(int(request.args.get('l', 25)), 100)
    page = max(int(request.args.get('page', 1)), 1)

    q = Channel.visible(
        Channel.query.filter(Channel.host == network),
        user=g.user
    ).order_by(Channel.created.desc())

    pagination = q.paginate(page, per_page, False)

    return render_template(
        'public/channels.html',
        per_page=per_page,
        network=network,
        pagination=pagination
    )


@public.route('/s/projects')
@public.route('/s/projects/<int:after>')
def projects(after: Optional[int] = None):
    per_page = min(int(request.args.get('l', 25)), 100)
    sort_by = request.args.get('s', 'created')

    # Reset any default ordering
    q = Project.visible(Project.query, user=g.user).order_by(False)
    match sort_by:
        case 'created':
            q = q.order_by(Project.created.desc())
            if after:
                q = q.filter(Project.created <= datetime.fromtimestamp(
                    int(after),
                    tz=timezone.utc
                ))
        case 'messages':
            q = q.order_by(Project.message_count.desc())
            if after:
                q = q.filter(Project.message_count <= int(after))
        case '_':
            return abort(400)

    results = q.limit(per_page + 1).all()

    next_page = None
    if len(results) == per_page + 1:
        next_page = url_for(
            '.projects',
            after=results[per_page].created.timestamp()
        )

    return render_template(
        'public/projects.html',
        projects=results[:per_page],
        next_page=next_page,
        per_page=per_page
    )


@public.route('/s/users', defaults={'page': 1})
@public.route('/s/users/<int:page>')
def users(page=1):
    per_page = min(int(request.args.get('l', 25)), 100)
    sort_by = request.args.get('s', 'created')

    q = User.query.order_by(False)
    q = q.order_by({
        'created': User.joined.desc()
    }.get(sort_by, User.joined.desc()))

    pagination = q.paginate(page, per_page, False)

    return render_template(
        'public/users.html',
        pagination=pagination,
        per_page=per_page
    )


@public.route('/s/services')
def services():
    return render_template(
        'public/services.html',
        services=available_services()
    )
