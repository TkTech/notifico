import hashlib
import datetime
import secrets

import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.hybrid import hybrid_property

from notifico.models import CaseInsensitiveComparator
from notifico.database import Base


class User(Base):
    __tablename__ = 'user'

    id = sa.Column(sa.Integer, primary_key=True)

    # ---
    # Required Fields
    # ---
    username = sa.Column(sa.String(50), unique=True, nullable=False)
    email = sa.Column(sa.String(255), nullable=False)
    password = sa.Column(sa.String(255), nullable=False)
    salt = sa.Column(sa.String(64), nullable=False)
    joined = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)

    # ---
    # Public Profile Fields
    # ---
    company = sa.Column(sa.String(255))
    website = sa.Column(sa.String(255))
    location = sa.Column(sa.String(255))

    @classmethod
    def new(cls, username, email, password):
        u = cls()
        u.email = email.lower().strip()
        u.salt = cls._create_salt()
        u.password = cls._hash_password(password, u.salt)
        u.username = username.strip()
        return u

    @staticmethod
    def _create_salt() -> str:
        return secrets.token_hex(32)

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """
        Returns a hashed password from `password` and `salt`.
        """
        h = hashlib.sha256()
        h.update(salt.encode('utf-8'))
        h.update(password.strip().encode('utf-8'))
        return h.hexdigest()

    def set_password(self, new_password):
        self.salt = self._create_salt()
        self.password = self._hash_password(new_password, self.salt)

    @classmethod
    def by_email(cls, email):
        return cls.query.filter_by(email=email.lower().strip()).first()

    @classmethod
    def by_username(cls, username):
        return cls.query.filter_by(username_i=username).first()

    @classmethod
    def email_exists(cls, email):
        return cls.query.filter_by(email=email.lower().strip()).count() >= 1

    @classmethod
    def username_exists(cls, username):
        return cls.query.filter_by(username_i=username).count() >= 1

    @classmethod
    def login(cls, username, password):
        """
        Returns a `User` object for which `username` and `password` are
        correct, otherwise ``None``.
        """
        u = cls.by_username(username)
        if u and u.password == cls._hash_password(password, u.salt):
            return u
        return None

    @hybrid_property
    def username_i(self):
        return self.username.lower()

    @username_i.comparator
    def username_i(cls):
        return CaseInsensitiveComparator(cls.username)

    def active_projects(self, limit=5):
        """
        Return this users most active projects (by descending message count).
        """
        q = self.projects.order_by(False).order_by('-message_count')
        q = q.limit(limit)
        return q

    def in_group(self, name):
        """
        Returns ``True`` if this user is in the group `name`, otherwise
        ``False``.
        """
        return any(g.name == name.lower() for g in self.groups)

    def add_group(self, name):
        """
        Adds this user to the group `name` if not already in it. The group
        will be created if needed.
        """
        if self.in_group(name):
            # We're already in this group.
            return

        self.groups.append(Group.get_or_create(name=name))


class Group(Base):
    __tablename__ = 'group'

    id = sa.Column(sa.Integer, primary_key=True)

    name = sa.Column(sa.String(255), unique=True, nullable=False)

    owner_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'))
    owner = orm.relationship(
        'User',
        backref=orm.backref(
            'groups',
            order_by=id,
            lazy='joined'
        )
    )

    def __repr__(self):
        return '<Group({name!r})>'.format(name=self.name)

    @classmethod
    def get_or_create(cls, name):
        name = name.lower()

        g = cls.query.filter_by(name=name).first()
        if not g:
            g = Group(name=name)

        return g
