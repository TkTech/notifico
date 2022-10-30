import datetime
import enum
from typing import Optional

from flask import g, url_for
import sqlalchemy as sa
from sqlalchemy import or_, orm
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Query

from notifico import has_permission
from notifico.database import Base
from notifico.models.util import CaseInsensitiveComparator
from notifico.permissions import HasPermissions, Action, Permission


class Project(Base, HasPermissions):
    class Page(enum.IntEnum):
        DETAILS = 10

    __tablename__ = 'project'

    id = sa.Column(sa.Integer, primary_key=True)

    name = sa.Column(sa.String(128), nullable=False)
    created = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)
    public = sa.Column(sa.Boolean, default=True)
    website = sa.Column(sa.String(1024))

    owner_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'))
    owner = orm.relationship(
        'User',
        backref=orm.backref(
            'projects',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    #: The total number of messages received by all hooks under this project,
    #: over all time.
    message_count = sa.Column(sa.Integer, default=0)

    @classmethod
    def new(cls, name, public=True, website=None):
        c = cls()
        c.name = name.strip()
        c.public = public
        c.website = website.strip() if website else None
        return c

    @hybrid_property
    def name_i(self):
        return self.name.lower()

    @name_i.comparator
    def name_i(cls):
        return CaseInsensitiveComparator(cls.name)

    @classmethod
    def by_name(cls, name):
        return cls.query.filter_by(name_i=name).first()

    @classmethod
    def by_name_and_owner(cls, name, owner):
        q = cls.query.filter(cls.owner_id == owner.id)
        q = q.filter(cls.name_i == name)
        return q.first()

    @classmethod
    def only_readable(cls, q: Query) -> Query:
        if has_permission(Permission.SUPERUSER):
            return q

        if g.user:
            q = q.filter(
                or_(
                    Project.public.is_(True),
                    Project.owner_id == g.user.id
                )
            )
        else:
            q = q.filter(Project.public.is_(True))

        return q

    @classmethod
    def can(cls, action: Action, *, obj: Optional['Project'] = None):
        if super().can(action, obj=obj):
            return True

        match action:
            case Action.CREATE:
                return True
            case Action.READ:
                if obj and g.user and obj.owner_id == g.user.id:
                    return True
            case Action.UPDATE | Action.DELETE:
                if obj and g.user and obj.owner_id == g.user.id:
                    return True

        return False

    def url(self, of: Page = Page.DETAILS) -> str:
        match of:
            case self.Page.DETAILS:
                return url_for(
                    'projects.details',
                    u=self.owner.username,
                    p=self.name
                )
            case _:
                raise ValueError(
                    f'Don\'t know how to generate a URL for {of=}.'
                )
