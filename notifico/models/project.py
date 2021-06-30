import datetime

from flask import url_for
from sqlalchemy.ext.hybrid import hybrid_property

from notifico.extensions import db
from notifico.models.log import HasLogs
from notifico.models.utils import CaseInsensitiveComparator


class Project(db.Model, HasLogs):
    """
    A Project is a logical collection of Sources and Channels.
    """
    id = db.Column(db.Integer, primary_key=True)

    #: A (hopefully) easily identifiable name for the project.
    name = db.Column(db.String(50), nullable=False)
    #: The date and time this project was created.
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)
    #: If true, this project can be viewed by anyone.
    public = db.Column(db.Boolean, default=True, server_default='t')
    #: A public website for this project.
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

    #: The total number of messages ever received on behalf of this project.
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
    def choose_source_url(self):
        return url_for('projects.choose_source', project=self)
