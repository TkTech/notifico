import click
from flask import current_app
from flask.cli import FlaskGroup

from notifico import create_instance, db
from notifico.models.user import User


@click.group(cls=FlaskGroup, create_app=create_instance)
def cli():
    """
    Management tool for Notifico.
    """


@cli.group()
def users():
    """User management commands."""


@users.command()
@click.argument('username')
@click.argument('email')
@click.option('--superuser', is_flag=True, default=False)
@click.password_option()
def create(username, email, password, superuser=False):
    """
    Create a new user.
    """
    user = User.new(username, email, password)
    if superuser:
        user.add_group('admin')

    db.session.add(user)
    db.session.commit()
