import flask_wtf as wtf
from flask_babel import lazy_gettext as _
from wtforms import fields, validators

from notifico.provider import get_providers


class ProjectDetailsForm(wtf.FlaskForm):
    name = fields.StringField('Project Name', validators=[
        validators.DataRequired(),
        validators.Length(1, 50),
        validators.Regexp(r'^[a-zA-Z0-9_\-\.]*$', message=(
            'Project name must only contain a to z, 0 to 9, dashes'
            ' and underscores.'
        ))
    ])
    public = fields.BooleanField(
        'Public',
        default=True,
        description=_(
            'If your project is public, other users will be able to see it'
            ' exists. However, you can still make your channels individually'
            ' public or private.'
        )
    )
    website = fields.StringField('Project URL', validators=[
        validators.Optional(),
        validators.Length(max=1024),
        validators.URL()
    ])


class NewProviderForm(wtf.FlaskForm):
    name = fields.StringField('Project Name', validators=[
        validators.DataRequired(),
        validators.Length(1, 50),
        validators.Regexp(r'^[a-zA-Z0-9_\-\.]*$', message=(
            'Project name must only contain a to z, 0 to 9, dashes'
            ' and underscores.'
        ))
    ])
