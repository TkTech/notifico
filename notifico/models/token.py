# -*- coding: utf8 -*-
__all__ = ('AuthToken',)
import datetime

from notifico import db


class AuthToken(db.Model):
    """
    Service authentication tokens, such as those used for Github's OAuth.
    """
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)
    name = db.Column(db.String(50), nullable=False)
    token = db.Column(db.String(512), nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship('User', backref=db.backref(
        'tokens', order_by=id, lazy='dynamic', cascade='all, delete-orphan'
    ))

    @classmethod
    def new(cls, token, name):
        c = cls()
        c.token = token
        c.name = name
        return c
