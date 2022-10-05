"""
A collection of utility methods for common site statistics.
"""
from sqlalchemy import func, text

from notifico import cache
from notifico.database import db_session
from notifico.models import Project, Channel, User


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
    return User.query.count()


@cache.memoize(timeout=60 * 5)
def total_projects():
    return Project.query.count()


@cache.memoize(timeout=60 * 5)
def total_networks():
    return db_session.query(
        func.count(func.distinct(Channel.host)).label('count')
    ).scalar()


@cache.memoize(timeout=60 * 5)
def total_channels():
    return db_session.query(
        func.count(Channel).label('count')
    ).scalar()


@cache.memoize(timeout=60 * 5)
def top_networks(limit=20):
    return (
        db_session.query(
            Channel.host,
            func.count(func.distinct(Channel.channel)).label('count'),
        )
        .join(Channel.project).filter(
            Project.public.is_(True),
            Channel.public.is_(True)
        )
        .group_by(Channel.host)
        .order_by(text('count desc'))
        .limit(limit)
    ).all()
