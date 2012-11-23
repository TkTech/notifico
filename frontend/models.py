# -*- coding: utf8 -*-
__all__ = ('User', 'Project', 'AuthToken', 'Hook')
import os
import base64
import hashlib
import datetime

from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from sqlalchemy import func

from frontend import db
from frontend.services import service_from_id


class CaseInsensitiveComparator(Comparator):
    def __eq__(self, other):
        return func.lower(self.__clause_element__()) == func.lower(other)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # ---
    # Required Fields
    # ---
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    salt = db.Column(db.String(8), nullable=False)
    joined = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow())

    # ---
    # Public Profile Fields
    # ---
    company = db.Column(db.String(255))
    website = db.Column(db.String(255))
    location = db.Column(db.String(255))

    @classmethod
    def new(cls, username, email, password):
        u = cls()
        u.email = email.lower().strip()
        u.salt = cls._create_salt()
        u.password = cls._hash_password(password, u.salt)
        u.username = username.strip()
        return u

    @staticmethod
    def _create_salt():
        """
        Returns a new base64 salt.
        """
        return base64.b64encode(os.urandom(8))[:8]

    @staticmethod
    def _hash_password(password, salt):
        """
        Returns a hashed password from `password` and `salt`.
        """
        return hashlib.sha256(salt + password.strip()).hexdigest()

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


class AuthToken(db.Model):
    """
    Service authentication tokens, such as those used for Github's OAuth.
    """
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow())
    name = db.Column(db.String(50), nullable=False)
    token = db.Column(db.String(512), nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref=db.backref(
        'tokens', order_by=id, lazy='dynamic'
    ))

    @classmethod
    def new(cls, token, name):
        c = cls()
        c.token = token
        c.name = name
        return c


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow())
    public = db.Column(db.Boolean, default=True)
    website = db.Column(db.String(1024))

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref=db.backref(
        'projects', order_by=id, lazy='dynamic'
    ))

    full_name = db.Column(db.String(101), nullable=False, unique=True)
    message_count = db.Column(db.Integer, default=0)

    @classmethod
    def new(cls, name, public=True, website=None):
        c = cls()
        c.name = name
        c.public = public
        c.website = website
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
    def public_q(cls):
        return cls.query.filter_by(public=True)

    @classmethod
    def private_q(cls):
        return cls.query.filter_by(public=False)


class Hook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow())
    key = db.Column(db.String(255), nullable=False)
    service_id = db.Column(db.Integer)

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship('Project', backref=db.backref(
        'hooks', order_by=id, lazy='dynamic'
    ))

    message_count = db.Column(db.Integer, default=0)

    @classmethod
    def new(cls, service_id):
        p = cls()
        p.service_id = service_id
        p.key = cls._new_key()
        return p

    @staticmethod
    def _new_key():
        return base64.urlsafe_b64encode(os.urandom(24))[:24]

    @classmethod
    def by_service_and_project(cls, service_id, project_id):
        return cls.query.filter_by(
            service_id=service_id,
            project_id=project_id
        ).first()

    @property
    def service(self):
        return service_from_id(self.service_id)
