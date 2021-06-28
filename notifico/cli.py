import click
from flask.cli import FlaskGroup

from notifico.app import create_app
from notifico.extensions import db


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management script for the notifico service."""


@cli.command('superuser')
@click.argument('username')
def superuser(username):
    """Make the given username an administrator."""
    from notifico.models.user import User

    u = User.query.filter(User.username_i == username).first()
    if not u:
        click.echo('No such user exists with that username')
        return

    yes = click.confirm(f'This will make {u.username} an admin. Are you sure?')
    if yes:
        u.is_admin = True
        db.session.commit()
        click.echo(f'{u.username} is now an admin.')


@cli.command('seed')
def seed():
    """Seeds the database with required data, such as the default user groups
    for anonymous and registered users.
    """
    from notifico.models.group import Group, Permission, CoreGroups

    db.session.add_all([
        Group(
            id=CoreGroups.ANONYMOUS.value,
            name='Anonymous',
            description=(
                'This group is used for permissions on users who are not'
                ' logged into the site.'
            ),
            deletable=False,
            permissions=[
                Permission.get('can_register')
            ]
        ),
        Group(
            id=CoreGroups.REGISTERED.value,
            name='Registered',
            description=(
                'This group is automatically applied to a user once they'
                ' register an account.'
            ),
            deletable=False,
            permissions=[
                Permission.get('create_project'),
                Permission.get('create_provider'),
                Permission.get('create_channel')
            ]
        )
    ])

    db.session.commit()
