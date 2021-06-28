from flask_wtf import FlaskForm
from flask_babel import lazy_gettext as _
from wtforms import fields, validators


def make_permission_form(permissions):
    """A helper for creating a WTForms Form that can handle a permission
    matrix.

    Since permissions are dynamic, we don't know what the fields are going
    to be until runtime.
    """
    class PermissionForm(FlaskForm):
        pass

    for permission, enabled in permissions.items():
        setattr(
            PermissionForm,
            permission.key,
            fields.BooleanField(default=enabled)
        )

    return PermissionForm


class GroupDetailsForm(FlaskForm):
    name = fields.StringField(
        _('Name'),
        validators=[
            validators.DataRequired(),
            validators.Length(max=255)
        ],
        description=_(
            'A human-friendly name for this group.'
        )
    )

    description = fields.StringField(
        _('Description'),
        validators=[
            validators.DataRequired(),
            validators.Length(max=2046)
        ],
        description=_(
            'A description of this group.'
        )
    )
