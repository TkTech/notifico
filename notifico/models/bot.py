import datetime

import sqlalchemy as sa

from notifico.database import Base


class BotEvent(Base):
    __tablename__ = 'bot_event'

    id = sa.Column(sa.Integer, primary_key=True)
    created = sa.Column(sa.TIMESTAMP(), default=datetime.datetime.utcnow)

    channel = sa.Column(sa.String(80))
    host = sa.Column(sa.String(255), nullable=False)
    port = sa.Column(sa.Integer, default=6667)
    ssl = sa.Column(sa.Boolean, default=False)

    message = sa.Column(sa.Text())
    status = sa.Column(sa.String(30))
    event = sa.Column(sa.String(255))

    @classmethod
    def new(cls, host, port, ssl, message, status, event, channel=None):
        c = cls()
        c.host = host
        c.port = port
        c.ssl = ssl
        c.message = message
        c.status = status
        c.event = event
        c.channel = channel
        return c
