import datetime

import sqlalchemy as sa
from sqlalchemy import func, text, orm

from notifico.database import Base, db_session
from notifico.models.bot import BotEvent


class Channel(Base):
    __tablename__ = 'channel'

    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)

    channel = sa.Column(sa.String(80), nullable=False)
    host = sa.Column(sa.String(255), nullable=False)
    port = sa.Column(sa.Integer, default=6667)
    ssl = sa.Column(sa.Boolean, default=False)
    public = sa.Column(sa.Boolean, default=False)

    project_id = sa.Column(sa.Integer, sa.ForeignKey('project.id'))
    project = orm.relationship(
        'Project',
        backref=orm.backref(
            'channels',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    @classmethod
    def new(cls, channel, host, port=6667, ssl=False, public=False):
        c = cls()
        c.channel = channel
        c.host = host
        c.port = port
        c.ssl = ssl
        c.public = public
        return c

    @classmethod
    def channel_count_by_network(cls):
        q = (
            db_session.query(
                Channel.host, func.count(Channel.channel).label('count')
            )
            .filter_by(public=True)
            .group_by(Channel.host)
            .order_by(text('-count'))
        )
        for network, channel_count in q:
            yield network, channel_count

    def last_event(self):
        """
        Returns the latest BotEvent to occur for this channel.
        """
        return BotEvent.query.filter_by(
            host=self.host,
            port=self.port,
            ssl=self.ssl,
            channel=self.channel
        ).order_by(BotEvent.created.desc()).first()

    @classmethod
    def visible(cls, q, user=None):
        """
        Modifies the sqlalchemy query `q` to only show channels accessible
        to `user`. If `user` is ``None``, only shows public channels in
        public projects.
        """
        from notifico.models import Project

        if user and user.in_group('admin'):
            # We don't do any filtering for admins,
            # who should have full visibility.
            pass
        else:
            q = q.join(Channel.project).filter(
                Project.public.is_(True),
                Channel.public.is_(True)
            )

        return q
