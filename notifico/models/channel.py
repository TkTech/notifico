import datetime
import enum
from datetime import timezone
from typing import Optional

from flask import g, url_for
import sqlalchemy as sa
from sqlalchemy import orm, or_
from sqlalchemy.orm import Query

from notifico import Action, has_permission
from notifico.database import Base
from notifico.permissions import HasPermissions, Permission


class IRCNetwork(Base, HasPermissions):
    class Page(enum.IntEnum):
        DETAILS = 10
        EDIT = 20

    class Status(enum.IntEnum):
        UNKNOWN = 0
        HEALTHY = 10
        DEGRADING = 20
        TEMPORARY_BLOCK = 30
        BLOCKED = 40

    __tablename__ = 'irc_network'

    id = sa.Column(sa.Integer, primary_key=True)

    host = sa.Column(sa.String(255), nullable=False)
    port = sa.Column(sa.Integer, default=6667)
    ssl = sa.Column(sa.Boolean, default=False)

    #: If > 0, this network should be visible to the public. The value is
    #: used as the sort ordering when presenting a list of networks.
    public = sa.Column(sa.Integer, default=0)

    owner_id = sa.Column(
        sa.BigInteger,
        sa.ForeignKey('user.id'),
        nullable=True
    )
    owner = orm.relationship(
        'User',
        backref=orm.backref(
            'networks',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    status = sa.Column(
        sa.Enum(Status),
        default=Status.UNKNOWN
    )

    created = sa.Column(
        sa.DateTime,
        default=lambda: datetime.datetime.now(tz=timezone.utc)
    )

    @classmethod
    def only_readable(cls, q: Query) -> Query:
        if has_permission(Permission.SUPERUSER):
            return q

        if g.user:
            return q.filter(
                or_(
                    IRCNetwork.owner_id == g.user.id,
                    IRCNetwork.public > 0
                )
            )
        else:
            return q.filter(IRCNetwork.public > 0)

    @classmethod
    def can(cls, action: Action, *, obj: Optional['IRCNetwork'] = None):
        if super().can(action, obj=obj):
            return True

        match action:
            case Action.READ:
                if g.user and obj:
                    return g.user_id == obj.owner_id or obj.public > 0
                elif obj:
                    return obj.public > 0
            case Action.UPDATE | Action.DELETE:
                if g.user and obj:
                    return g.user.id == obj.owner_id
            case Action.CREATE:
                return True

        return False

    def url(self, of: Page = Page.DETAILS) -> str:
        match of:
            case self.Page.EDIT:
                return url_for(
                    'settings.irc_network_edit',
                    network_id=self.id
                )
            case _:
                raise ValueError(
                    f'Don\'t know how to generate a URL for {of=}.'
                )


class NetworkEvent(Base):
    class Event(enum.IntEnum):
        CRITICAL = 100
        ERROR = 200
        WARNING = 300
        INFO = 400

    __tablename__ = 'network_event'

    id = sa.Column(sa.Integer, primary_key=True)

    event = sa.Column(sa.Enum(Event))
    description = sa.Column(sa.Text(), nullable=True)

    created = sa.Column(
        sa.DateTime,
        default=lambda: datetime.datetime.now(tz=timezone.utc)
    )

    network_id = sa.Column(sa.BigInteger, sa.ForeignKey('irc_network.id'))
    network = orm.relationship(
        'IRCNetwork',
        backref=orm.backref(
            'events',
            order_by=created,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )


class Channel(Base, HasPermissions):
    __tablename__ = 'channel'

    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)

    channel = sa.Column(sa.String(80), nullable=False)
    public = sa.Column(sa.Boolean, default=False)

    network_id = sa.Column(sa.BigInteger, sa.ForeignKey('irc_network.id'))
    network = orm.relationship(
        'IRCNetwork',
        backref=orm.backref(
            'channels',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

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
    def only_readable(cls, q: Query) -> Query:
        if has_permission(Permission.SUPERUSER):
            return q

        if g.user:
            return q.join(
                Channel.project
            ).filter(
                or_(
                    Channel.public.is_(True),
                    Channel.project.owner_id == g.user.id
                )
            )
        else:
            return q.filter(Channel.public.is_(True))

    @classmethod
    def can(cls, action: Action, *, obj: 'Channel' = None):
        if super().can(action, obj=obj):
            return True

        match action:
            case Action.READ:
                if g.user and obj:
                    return g.user.id == obj.project.owner_id or obj.public
                elif obj:
                    return obj.public
            case Action.UPDATE | Action.DELETE:
                if g.user and obj:
                    return g.user.id == obj.project.owner_id
            case Action.CREATE:
                return True

        return False
