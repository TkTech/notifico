"""
A collection of utility methods for common site statistics.
"""
from sqlalchemy import func, text

from notifico import cache
from notifico.database import db_session
from notifico.models import Project, Channel, User, IRCNetwork


@cache.memoize(timeout=60 * 5)
def total_messages(user=None):
    """
    Sum the total number of messages across all projects.
    """
    q = db_session.query(
        func.sum(Project.message_count)
    )
    if user:
        q = q.filter(Project.owner_id == user.id)

    return q.scalar() or 0


@cache.memoize(timeout=60 * 5)
def total_users():
    return db_session.query(func.count(User.id)).scalar()


@cache.memoize(timeout=60 * 5)
def total_projects():
    return db_session.query(func.count(Project.id)).scalar()


@cache.memoize(timeout=60 * 5)
def total_networks():
    return db_session.query(func.count(IRCNetwork.id)).scalar()


@cache.memoize(timeout=60 * 5)
def total_channels():
    return db_session.query(
        Channel
    ).distinct(
        Channel.channel,
        Channel.network_id
    ).count()
