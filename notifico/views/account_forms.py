from flask import g
import flask_wtf as wtf
from wtforms import fields, validators

from notifico.models import User
from notifico.services import reset


class UserRegisterForm(wtf.FlaskForm):
    username = fields.StringField('Username', validators=[
        validators.InputRequired(),
        validators.Length(min=2, max=50),
        validators.Regexp('^[a-zA-Z0-9_]*$', message=(
            'Username must only contain a to z, 0 to 9, and underscores.'
        ))
    ], description=(
        'Your username is public and used as part of your project name.'
    ))
    email = fields.StringField('Email', validators=[
        validators.InputRequired(),
        validators.Email()
    ])
    password = fields.PasswordField('Password', validators=[
        validators.InputRequired(),
        validators.Length(5),
        validators.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = fields.PasswordField('Confirm Password')

    def validate_username(form, field):
        from notifico.views.account import _reserved

        username = field.data.strip().lower()
        if username in _reserved or User.username_exists(username):
            raise validators.ValidationError(
                'Sorry, but that username is taken.'
            )


class UserLoginForm(wtf.FlaskForm):
    username = fields.StringField('Username', validators=[
        validators.InputRequired()
    ])
    password = fields.PasswordField('Password', validators=[
        validators.InputRequired()
    ])

    def validate_password(form, field):
        if not User.login(form.username.data, field.data):
            raise validators.ValidationError(
                'Incorrect username and/or password.'
            )


class UserPasswordForm(wtf.FlaskForm):
    old = fields.PasswordField('Old Password', validators=[
        validators.InputRequired(),
    ])
    password = fields.PasswordField('Password', validators=[
        validators.InputRequired(),
        validators.Length(5),
        validators.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = fields.PasswordField('Confirm Password')

    def validate_old(form, field):
        if not User.login(g.user.username, field.data):
            raise validators.ValidationError('Old Password is incorrect.')


class UserDeleteForm(wtf.FlaskForm):
    password = fields.PasswordField('Password', validators=[
        validators.InputRequired(),
        validators.Length(5),
        validators.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = fields.PasswordField('Confirm Password')

    def validate_password(form, field):
        if not User.login(g.user.username, field.data):
            raise validators.ValidationError('Password is incorrect.')


class UserForgotForm(wtf.FlaskForm):
    username = fields.StringField('Username', validators=[
        validators.InputRequired()
    ])

    def validate_username(form, field):
        user = User.by_username(field.data)
        if not user:
            raise validators.ValidationError('No such user exists.')

        if reset.count_tokens(user) >= 5:
            raise validators.ValidationError(
                'You may not reset your password more than 5 times'
                ' in one day.'
            )


class UserResetForm(wtf.FlaskForm):
    password = fields.PasswordField('New Password', validators=[
        validators.InputRequired(),
        validators.Length(5),
        validators.EqualTo('confirm', 'Passwords do not match.'),
    ])
    confirm = fields.PasswordField('Confirm Password')
