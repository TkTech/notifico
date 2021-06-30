import os
import base64
import datetime
from typing import Optional

from flask import url_for

from notifico.extensions import db
from notifico.models.log import HasLogs
from notifico.plugin import get_installed_sources


def _new_random_key():
    return base64.urlsafe_b64encode(os.urandom(24))[:24].decode('ascii')


source_groups = db.Table(
    'source_groups',
    db.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('source_id', db.Integer, db.ForeignKey('source.source_id'))
)


class Source(db.Model):
    """
    Global configuration for Sources.
    """
    #: The unique, global ID of the source. Must not change, unless
    #: accompanied by a migration.
    source_id = db.Column(db.Integer, primary_key=True)

    #: A source's form data will be stored on this form. Presented only to
    #: administrators, and can be used for things like only allowing Github
    #: hooks if they come from a whitelist of IPs.
    config = db.Column(db.JSON, server_default='{}')

    #: If true, this source is available to users and can be selected for
    #: a new SourceInstance.
    enabled = db.Column(db.Boolean, default=False, server_default='f')

    #: Only members of these groups can use this provider.
    groups = db.relationship('Group', secondary=source_groups, lazy='dynamic')

    @property
    def implementation(self):
        return get_installed_sources()[self.source_id]

    @property
    def impl(self):
        """Shorthand for the `implementation()` property."""
        return self.implementation

    @property
    def admin_edit_url(self):
        return url_for('admin.sources_edit', source_id=self.source_id)


class SourceInstance(db.Model, HasLogs):
    """
    A configured instance of the source, attached to a specific project.
    """
    id = db.Column(db.Integer, primary_key=True)

    #: The time this source was first created.
    created = db.Column(db.TIMESTAMP(), default=datetime.datetime.utcnow)

    #: The Source that is responsible for this channel.
    source_id = db.Column(
        db.Integer,
        db.ForeignKey('source.source_id'),
        nullable=False
    )

    #: A source's form data will be stored on this form.
    config = db.Column(db.JSON)

    #: A unique value used to identify this source when a webhook is
    #: received.
    key = db.Column(db.String(255), default=_new_random_key)

    #: The last time a message was emitted by this source.
    last_message_received = db.Column(db.DateTime, nullable=True)
    #: The total number of events ever received by this source.
    events_received = db.Column(db.BigInteger, default=0, server_default='0')
    #: An indicator of health of this source. A healthy channel will be 1,
    #: an unhealthy channel with be 0 or less. Each time an event fails, this
    #: will decrement by 1.
    health = db.Column(db.Integer, default=1, server_default='1')

    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    project = db.relationship(
        'Project',
        backref=db.backref(
            'sources',
            lazy='dynamic',
            cascade='all, delete-orphan'
        )
    )

    source = db.relationship(
        'Source',
        backref=db.backref(
            'instances',
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
    def implementation(self):
        # We want this to be a hard error, don't use get(). Migrates should
        # be removing destroyed sources entirely, the usual case is to
        # always keep sources and to just disable them.
        return get_installed_sources()[self.source_id]

    @property
    def impl(self):
        """Shorthand for the `implementation()` property."""
        return self.implementation

    @property
    def description(self) -> Optional[str]:
        """A short, user-provided nickname or description for this source,
        to better help them identify it from a list of identical sources.

        May also be set automatically from import/sync tools.
        """
        # By convention, every source will have a description field in their
        # configuration, although it is not required.
        return self.config.get('description')

    @property
    def edit_url(self):
        return url_for(
            'projects.edit_source',
            project=self.project,
            source=self.id
        )

    @property
    def get_webhook_url(self):
        return url_for(
            'projects.get_source_url',
            project=self.project,
            source=self.id
        )
