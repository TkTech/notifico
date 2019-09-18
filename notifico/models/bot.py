# -*- coding: utf8 -*-
__all__ = ('BotEvent',)
import datetime

from notifico import db


class BotEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)

    channel = db.Column(db.String(80))
    host = db.Column(db.String(255), nullable=False)
    port = db.Column(db.Integer, default=6667)
    password = db.Column(db.String(255), nullable=True)
    ssl = db.Column(db.Boolean, default=False)

    message = db.Column(db.Text())
    status = db.Column(db.String(30))
    event = db.Column(db.String(255))

    @classmethod
    def new(cls, host, port, password, ssl, message, status, event, channel=None):
        c = cls()
        c.host = host
        c.port = port
        c.password = password
        c.ssl = ssl
        c.message = message
        c.status = status
        c.event = event
        c.channel = channel
        return c
