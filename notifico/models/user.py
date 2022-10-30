import hashlib
import datetime
import secrets
from typing import Optional

from flask import g, current_app
import sqlalchemy as sa
from sqlalchemy import orm
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Query

from notifico.models.util import CaseInsensitiveComparator
from notifico.database import Base
from notifico.permissions import HasPermissions, Action

role_association = sa.Table(
    'role_association',
    Base.metadata,
    sa.Column('user_id', sa.ForeignKey('user.id')),
    sa.Column('role_id', sa.ForeignKey('role.name'))
)

permission_association = sa.Table(
    'permission_association',
    Base.metadata,
    sa.Column('role_id', sa.ForeignKey('role.name')),
    sa.Column('permission_id', sa.ForeignKey('permission.name'))
)


class User(Base, HasPermissions):
    __tablename__ = 'user'

    id = sa.Column(sa.Integer, primary_key=True)

    username = sa.Column(sa.String(50), unique=True, nullable=False)
    email = sa.Column(sa.String(255), nullable=False)
    password = sa.Column(sa.String(255), nullable=False)
    salt = sa.Column(sa.String(64), nullable=False)
    joined = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)

    roles = orm.relationship(
        'Role',
        secondary=role_association
    )
    permissions = orm.relationship(
        'Permission',
        secondary=(
            'join(role_association, permission_association,'
            'role_association.c.role_id == permission_association.c.role_id)'
        ),
        viewonly=True,
        lazy='joined'
    )

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

    @classmethod
    def only_readable(cls, q: Query) -> Query:
        # We allow user listing by default.
        return q

    @classmethod
    def can(cls, action: Action, *, obj: Optional['User'] = None):
        if super().can(action, obj=obj):
            return True

        match action:
            case Action.CREATE:
                return current_app.config.get('NEW_USERS', True)
            case Action.READ | Action.DELETE | Action.UPDATE:
                if obj and g.user and g.user.id == obj.id:
                    return True

        return False


class Permission(Base):
    __tablename__ = 'permission'

    name = sa.Column(sa.String(255), primary_key=True)


class Role(Base):
    __tablename__ = 'role'

    name = sa.Column(sa.String(255), primary_key=True)
    permissions = orm.relationship(
        'Permission',
        secondary=permission_association
    )
