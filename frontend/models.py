# -*- coding: utf8 -*-
__all__ = ('User',)
import os
import base64
import hashlib
import datetime

from frontend import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # ---
    # Required Fields
    # ---
    email = db.Column(db.String(255), unique=True, nullable=False)
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
    def new(cls, email, password):
        u = cls()
        u.email = email
        u.salt = cls._create_salt()
        u.password = cls._hash_password(password, u.salt)
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

    @classmethod
    def by_email(cls, email):
        return cls.query.filter_by(email=email.lower().strip()).first()

    @classmethod
    def exists_email(cls, email):
        return cls.query.filter_by(email=email.lower().strip()).count() >= 1

    @classmethod
    def login(cls, email, password):
        u = cls.by_email(email)
        if u and u.password == cls._hash_password(password, u.salt):
            return u
        return None
