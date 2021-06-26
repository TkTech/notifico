import datetime

from flask import url_for
from sqlalchemy.ext.hybrid import hybrid_property

from notifico.extensions import db
from notifico.models import CaseInsensitiveComparator
from notifico.models.log import HasLogs


class Project(db.Model, HasLogs):
    """
    A project is a collection of Providers (which emit events) and Channels
    (which receives processed events).
    """
    __tablename__ = 'project'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)
    public = db.Column(db.Boolean, default=True)
    website = db.Column(db.String(1024))

    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    owner = db.relationship(
        'User',
        backref=db.backref(
            'projects',
            order_by=id,
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    message_count = db.Column(db.Integer, default=0)

    #: The last time a message was received for this project, from any
    #: source.
    last_message_recieved = db.Column(db.DateTime, nullable=True)

    #: An indicator of health on this project. If hooks (to or from) are
    #: erroring, this will be set to 0. A healthy project will be 1.
    health = db.Column(db.Integer, default=1, server_default='1')

    __table_args__ = (
        db.Index('uidx_name_owner', 'name', 'owner_id', unique=True),
    )

    @hybrid_property
    def name_i(self):
        return self.name.lower()

    @name_i.comparator
    def name_i(cls):
        return CaseInsensitiveComparator(cls.name)

    @property
    def details_url(self):
        return url_for('projects.details', project=self)

    @property
    def edit_url(self):
        return url_for('projects.edit_project', project=self)

    @property
    def delete_url(self):
        return url_for('projects.delete_project', project=self)

    @property
    def choose_provider_url(self):
        return url_for('projects.choose_provider', project=self)
