from enum import Enum

from flask import url_for

from notifico.extensions import db
from notifico.permissions import PERMISSIONS
from notifico.models.utils import get_or_create


class ValueType(Enum):
    STRING = 10
    INTEGER = 20
    FLOAT = 30
    BOOLEAN = 40


class CoreGroups(Enum):
    """Database IDs for core groups, which are guaranteed to both exist,
    and to have the given ID.
    """
    ANONYMOUS = 1
    REGISTERED = 2


group_permission = db.Table(
    'group_permission',
    db.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
)

group_limit = db.Table(
    'group_limit',
    db.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('limit_id', db.Integer, db.ForeignKey('limit.id'))
)

group_members = db.Table(
    'group_members',
    db.metadata,
    db.Column('group_id', db.Integer, db.ForeignKey('group.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)


class Limit(db.Model):
    """
    Unlike permissions, which are a simple can or cannot, Limits are typically
    used to specifiy maximums and/or minimums. A limit can be used to stop
    registered users from making more than a thousand projects, for example.
    """
    id = db.Column(db.Integer, primary_key=True)

    #: A short, machine-friendly name for this limit, such as
    #: "maximum_channels".
    key = db.Column(db.String(255), nullable=False)

    #: The type of value stored by this limit.
    value_type = db.Column(db.Enum(ValueType))

    #: The JSON-encoded value of type `value_type`.
    value = db.Column(db.JSON)


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    #: A short, unique, human-friendly name for this permission, such as
    #: "Can Create Projects".
    name = db.Column(db.String(2500), nullable=False, unique=True)

    #: A short, unique, machine-friendly name for this permission, such as
    #: "can_create_projects".
    key = db.Column(db.String(150), nullable=False, unique=True)

    #: A human-readable description of what granting this permission would
    #: enable.
    description = db.Column(db.Text)

    @classmethod
    def get(cls, key):
        """
        Gets or creates the permission given by `key`, using the defaults
        from `notifico.permissions` if it is missing.
        """
        # We want to error if the permission isn't defined, someone screwed
        # up.
        defaults = PERMISSIONS[key]

        return get_or_create(
            db.session,
            cls,
            {'key': key},
            defaults={
                'key': key,
                'name': defaults.name,
                'description': defaults.description
            }
        )


class Group(db.Model):
    """
    A group associates one or more users with a set of permissions and limits.
    Modifying the permissions or limits in the group affects all users that
    are part of the group.

    Users can be given individual permissions and/or limits that will superceed
    the base set they get from associated groups.
    """
    id = db.Column(db.Integer, primary_key=True)

    #: A human-friendly name for this group.
    name = db.Column(db.String(255), nullable=False, unique=True)

    #: A human-friendly description of this group.
    description = db.Column(db.Text)

    #: If False, this group cannot be deleted. Used to protect default user
    #: groups such as anonymous and registered.
    deletable = db.Column(db.Boolean, default=True, server_default='t')

    #: The permissions users in this group will receive.
    permissions = db.relationship('Permission', secondary=group_permission)

    #: The limits users in this group will receive.
    limits = db.relationship('Limit', secondary=group_limit)

    #: All of the users that have membership in this group.
    users = db.relationship(
        'User',
        secondary=group_members,
        lazy='dynamic',
        backref=db.backref(
            'groups',
            lazy='joined'
        )
    )

    def permission_matrix(self):
        perms = {perm.key for perm in self.permissions}
        return {
            permission: (key in perms)
            for key, permission in PERMISSIONS.items()
        }

    @property
    def edit_url(self):
        return url_for('admin.groups_edit', group_id=self.id)

    @property
    def delete_url(self):
        return url_for('admin.groups_delete', group_id=self.id)
