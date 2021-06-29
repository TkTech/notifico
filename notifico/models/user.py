import os
import base64
import hashlib
import datetime

from flask import url_for
from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property

from notifico.extensions import db
from notifico.models.utils import CaseInsensitiveComparator


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False)
    #: The user's currently active email address.
    email = db.Column(db.String(255), nullable=False)
    #: The salted and hashed user password.
    password = db.Column(db.String(255), nullable=False)
    #: The salt used to hash `passworc`.
    salt = db.Column(db.String(8), nullable=False)

    #: The date and time this user was created.
    joined = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)

    #: If True, this user skips all permission checks.
    is_admin = db.Column(db.Boolean, default=False, server_default='f')

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

    @property
    def dashboard_url(self):
        return url_for('projects.dashboard', user=self)

    @property
    def admin_edit_url(self):
        return url_for('admin.users_edit', user_id=self.id)

    def get_id(self) -> str:
        # Part of the flask_login.UserMixin interface.
        return str(self.id)
