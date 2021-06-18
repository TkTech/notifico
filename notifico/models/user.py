import os
import base64
import hashlib
import datetime

from flask import url_for
from sqlalchemy.ext.hybrid import hybrid_property

from notifico import db
from notifico.models import CaseInsensitiveComparator


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # ---
    # Required Fields
    # ---
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    salt = db.Column(db.String(8), nullable=False)
    joined = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)

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
    def _hash_password(password, salt) -> str:
        """
        Returns a hashed password from `password` and `salt`.
        """
        if isinstance(salt, str):
            salt = salt.encode('utf-8')

        if isinstance(password, str):
            password = password.encode('utf-8')

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
        Return this users most active projets (by descending message count).
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

    @property
    def dashboard_url(self):
        return url_for('projects.dashboard', u=self.username)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), unique=True, nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref=db.backref(
        'groups', order_by=id, lazy='joined'
    ))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Group({name!r})>'.format(name=self.name)

    @classmethod
    def get_or_create(cls, name):
        name = name.lower()

        g = cls.query.filter_by(name=name).first()
        if not g:
            g = Group(name=name)

        return g
