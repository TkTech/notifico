from flask import url_for

from notifico.extensions import db
from notifico.plugins.core import all_available_plugins


plugin_groups = db.Table(
    'plugin_groups',
    db.metadata,
    db.Column('plugin_id', db.String(255), db.ForeignKey('plugin.plugin_id')),
    db.Column('group_id', db.Integer, db.ForeignKey('group.id'))
)


class Plugin(db.Model):
    __tablename__ = 'plugin'

    # A numerical primary key is still required (even if plugin_id would be
    # a good key) in order to fit with our LogContext pattern.
    id = db.Column(db.Integer, primary_key=True)
    #: The unique ID for the plugin. No two plugins of the same type
    #: should share the same plugin_id.
    plugin_id = db.Column(db.String(255), unique=True)
    #: Arbitrary configuration for the plugin. This configuration is usable
    #: by all instances of the plugin, but can only be edited by an Admin.
    config = db.Column(db.JSON, server_default='{}')
    #: If True, this plugin should be enabled.
    enabled = db.Column(db.Boolean, default=False, server_default='f')
    #: Used to restrict plugins to a particular set of groups. If it does
    #: not make sense for a plugin to have access restrictions, the plugin
    #: is free to ignore it.
    groups = db.relationship(
        'Group',
        secondary=plugin_groups,
        lazy='dynamic',
        backref=db.backref(
            'plugins',
            lazy='dynamic'
        )
    )

    @property
    def impl(self):
        return all_available_plugins().get(self.plugin_id)

    @property
    def meta(self):
        return self.impl.metadata()

    @property
    def admin_edit_url(self):
        return url_for('admin.plugins_edit', plugin_id=self.id)
