from typing import Iterable

from flask import Blueprint, render_template
from sqlalchemy import func, text

from notifico import Permission, db_session
from notifico.models import IRCNetwork
from notifico.permissions import require_permission

admin_view = Blueprint('admin', __name__)


@admin_view.route('/')
@require_permission(Permission.SUPERUSER)
def dashboard():
    return render_template('admin/base.html')


@admin_view.route(
    '/irc/networks',
    endpoint='irc_networks',
    methods=['GET', 'POST']
)
@require_permission(Permission.SUPERUSER)
def irc_networks_page():
    """
    Administrative view for managing IRC networks.
    """
    networks: Iterable[IRCNetwork] = db_session.query(
        IRCNetwork,
        func.count(IRCNetwork.channels).label('count')
    ).outerjoin(
        IRCNetwork.channels
    ).group_by(
        IRCNetwork.id
    ).order_by(
        text('count DESC')
    ).all()

    return render_template(
        'admin/irc_networks.html',
        networks=networks
    )