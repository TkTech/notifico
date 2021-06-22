import os
import base64
import datetime

from sqlalchemy.schema import UniqueConstraint

from notifico import db
from notifico.provider import get_providers, ProviderTypes


def _new_random_key():
    return base64.urlsafe_b64encode(os.urandom(24))[:24].decode('ascii')


class Provider(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    #: The time this provider was first created.
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)

    #: The Provider that is responsible for this channel.
    provider_id = db.Column(db.Integer, nullable=False)

    #: The type of provider.
    provider_type = db.Column(db.Enum(ProviderTypes), nullable=False)

    #: A provider's form data will be stored on this form.
    config = db.Column(db.JSON)

    #: A unique value used to identify this provider when a webhook is
    #: received.
    key = db.Column(db.String(255), default=_new_random_key)

    #: The last time a message was emitted by this provider.
    last_message_received = db.Column(db.DateTime, nullable=True)
    #: The total number of events ever received by this provider.
    events_received = db.Column(db.BigInteger, default=0, server_default='0')
    #: An indicator of health of this provider. A healthy channel will be 1,
    #: an unhealthy channel with be 0 or less. Each time an event fails, this
    #: will decrement by 1.
    health = db.Column(db.Integer, default=1, server_default='1')

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship(
        'Project',
        backref=db.backref(
            'providers',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    __table_args__ = (
        # Our webhook URLs are a combination of the project_id and the key,
        # so ensure that every URL within a project will be unique.
        db.Index('uidx_id_key', 'project_id', 'key', unique=True),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def provider(self):
        return get_providers().get(self.provider_id)
