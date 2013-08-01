# -*- coding: utf8 -*-
__all__ = ('Project',)
import datetime

from sqlalchemy import or_
from sqlalchemy.ext.hybrid import hybrid_property

from notifico import db
from notifico.models import CaseInsensitiveComparator


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)
    public = db.Column(db.Boolean, default=True)
    website = db.Column(db.String(1024))

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref=db.backref(
        'projects', order_by=id, lazy='dynamic', cascade='all, delete-orphan'
    ))

    full_name = db.Column(db.String(101), nullable=False, unique=True)
    message_count = db.Column(db.Integer, default=0)

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
    def visible(cls, q, user=None):
        """
        Modifies the sqlalchemy query `q` to only show projects accessible
        to `user`. If `user` is ``None``, only shows public projects.
        """
        if user and user.in_group('admin'):
            # We don't do any filtering for admins,
            # who should have full visibility.
            pass
        elif user:
            # We only show the projects that are either public,
            # or are owned by `user`.
            q = q.filter(or_(
                Project.owner_id == user.id,
                Project.public == True
            ))
        else:
            q = q.filter(Project.public == True)

        return q

    def is_owner(self, user):
        """
        Returns ``True`` if `user` is the owner of this project.
        """
        return user and user.id == self.owner.id

    def can_see(self, user):
        if self.public:
            # Public projects are always visible.
            return True
        if user and user.in_group('admin'):
            # Admins can always see projects.
            return True
        elif self.is_owner(user):
            # The owner of the project can always see it.
            return True

        return False

    def can_modify(self, user):
        """
        Returns ``True`` if `user` can modify this project.
        """
        if user and user.in_group('admin'):
            # Admins can always modify projects.
            return True
        elif self.is_owner(user):
            return True

        return False
