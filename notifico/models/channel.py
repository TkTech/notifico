import os
import enum
import base64
import datetime
from typing import Optional

from notifico.extensions import db


def _new_random_key():
    return base64.urlsafe_b64encode(os.urandom(24))[:24].decode('ascii')


class ChannelDirection(enum.Enum):
    INBOUND = 10
    OUTBOUND = 20


class Channel(db.Model):
    """
    A configured Channel. Channels can be inbound (such as a webhook) or
    outbound.
    """
    id = db.Column(db.Integer, primary_key=True)

    #: The time this channel was first created.
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)
    #: Whether this channel is inbound or outbound.
    direction = db.Column(db.Enum(ChannelDirection), nullable=False)
    #: A channel's form data will be stored on this form.
    config = db.Column(db.JSON, default=dict, server_default='{}')
    #: The last time a message was sent or received by this channel.
    events_last_seen = db.Column(db.DateTime, nullable=True)
    #: The total number of events ever processed by this channel.
    events_received = db.Column(db.BigInteger, default=0, server_default='0')
    #: An indicator of health of this channel. A healthy channel will be 1,
    #: an unhealthy channel with be 0 or less. Each time an event fails, this
    #: will decrement by 1.
    health = db.Column(db.Integer, default=1, server_default='1')
    #: A unique value used to identify this source when a webhook is
    #: received.
    key = db.Column(db.String(255), default=_new_random_key)

    #: The Project that owns this channel.
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship(
        'Project',
        backref=db.backref(
            'channels',
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    #: The Plugin that implements this channel.
    plugin_id = db.Column(db.String(255), db.ForeignKey('plugin.plugin_id'))
    plugin = db.relationship(
        'Plugin',
        backref=db.backref(
            'channels',
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    __table_args__ = (
        # Our webhook URLs are a combination of the project_id and the key,
        # so ensure that every URL within a project will be unique.
        db.Index('uidx_id_key', 'project_id', 'key', unique=True),
    )

    @property
    def description(self) -> Optional[str]:
        """A short, user-provided nickname or description for this channel,
        to better help them identify it from a list of identical channels.

        May also be set automatically from import/sync tools.
        """
        # By convention, every channel will have a description field in their
        # configuration, although it is not required.
        return self.config.get('description')
