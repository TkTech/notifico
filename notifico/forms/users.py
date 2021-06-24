import flask_wtf as wtf
from flask_babel import lazy_gettext as _
from wtforms import fields, validators

from notifico.models.user import User


class UserRegisterForm(wtf.FlaskForm):
    username = fields.StringField(_('Username'), validators=[
        validators.DataRequired(),
        validators.Length(min=2, max=50),
        validators.Regexp('^[a-zA-Z0-9_]*$', message=_(
            'Username must only contain a to z, 0 to 9, and underscores.'
        ))
    ], description=_(
        'Your username is public and used as part of your project name.'
    ))
    email = fields.StringField(
        _('Email'),
        validators=[
            validators.DataRequired(),
            validators.Email()
        ],
        description=_(
            'We\'ll only email you if you request it (such as a password'
            ' reset) or for account security.'
        )
    )
    password = fields.PasswordField(
        _('Password'),
        validators=[
            validators.DataRequired(),
            validators.Length(5),
            validators.EqualTo('confirm', 'Passwords do not match.'),
        ]
    )
    confirm = fields.PasswordField(_('Confirm Password'))

    def validate_username(form, field):
        from notifico.views.users import _reserved

        username = field.data.strip().lower()
        if username in _reserved or User.username_exists(username):
            raise validators.ValidationError(
                'Sorry, but that username is taken.'
            )


class UserLoginForm(wtf.FlaskForm):
    username = fields.StringField(
        _('Username'),
        validators=[
            validators.DataRequired()
        ]
    )
    password = fields.PasswordField(
        _('Password'),
        validators=[
            validators.DataRequired()
        ]
    )

    def validate_password(form, field):
        if not User.login(form.username.data, field.data):
            raise validators.ValidationError(
                _('Incorrect username and/or password.')
            )
