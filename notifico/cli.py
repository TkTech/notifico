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
    from notifico.extensions import db
    from notifico.plugin import get_installed_sources
    from notifico.models.utils import get_or_create
    from notifico.models.source import Source
    from notifico.models.group import Group, Permission, CoreGroups

    if not Group.query.get(CoreGroups.ANONYMOUS.value):
        db.session.add(Group(
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
        ))

    if not Group.query.get(CoreGroups.REGISTERED.value):
        db.session.add(Group(
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
        ))

    db.session.commit()

    registered_group = db.session.query(Group).get(CoreGroups.REGISTERED.value)

    for source_id, source in get_installed_sources().items():
        get_or_create(
            db.session,
            Source,
            {'source_id': source_id},
            {'source_id': source_id, 'groups': [registered_group]}
        )
