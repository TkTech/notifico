import datetime

from notifico.extensions import db


class Target(db.Model):
    id = db.Column(db.BigInteger, primary_key=True)

    #: The date this channel was first created.
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)

    #: The last time a message was sent to this channel, from any source.
    last_message_sent = db.Column(db.DateTime, nullable=True)

    #: An indicator of health of this channel. A healthy channel will be 1,
    #: an unhealthy channel with be 0 or less.
    health = db.Column(db.Integer, default=1, server_default='1')

    #: The Target that is responsible for this channel.
    target_id = db.Column(db.Integer)

    #: A Channel can be handled by pluggable providers. The provider can
    #: store any needed information on this field.
    config = db.Column(db.JSON)

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship(
        'Project',
        backref=db.backref(
            'targets',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )
