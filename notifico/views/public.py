# -*- coding: utf-8 -*-
from flask import (
    Blueprint,
    render_template,
    g,
    request
)
from flask_sqlalchemy import Pagination
from sqlalchemy import func, text

from notifico import db
from notifico.service import available_services
from notifico.services import stats
from notifico.models import User, Channel, Project

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
    ).paginate(1, 10, False)

    return render_template(
        'public/landing.html',
        new_projects=new_projects,
        top_networks=stats.top_networks(limit=10),
        total_networks=stats.total_networks(),
        total_users=stats.total_users()
    )


@public.route('/s/networks/')
def networks():
    per_page = min(int(request.args.get('l', 25)), 100)
    page = max(int(request.args.get('page', 1)), 1)

    q = (
        Channel.visible(db.session.query(
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


@public.route('/s/projects', defaults={'page': 1})
@public.route('/s/projects/<int:page>')
def projects(page=1):
    per_page = min(int(request.args.get('l', 25)), 100)
    sort_by = request.args.get('s', 'created')

    q = Project.visible(Project.query, user=g.user).order_by(False)
    q = q.order_by({
        'created': Project.created.desc(),
        'messages': Project.message_count.desc()
    }.get(sort_by, Project.created.desc()))

    pagination = q.paginate(page, per_page, False)

    return render_template(
        'public/projects.html',
        pagination=pagination,
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
