import asyncio
import logging
import datetime

import click
from flask.cli import FlaskGroup

from notifico import create_app
from notifico.database import db_session
from notifico.models import Project, Role, Permission
from notifico.models.user import User


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """
    Management tool for Notifico.
    """


@cli.group()
def users():
    """User management commands."""


@cli.group()
def tools():
    """Misc. tools."""


@cli.group()
def bots():
    """Bot management commands."""


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

    db_session.add(user)
    db_session.commit()


@users.command('grant-role')
@click.argument('username')
@click.argument('role')
def grant_role(username: str, role: str):
    """
    Grants a user a specific role. Does nothing if the user already has the
    role.
    """
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        click.echo('No such user.')
        return

    role = db_session.query(Role).filter(Role.name == role).first()
    if not role:
        click.echo('No such role.')
        return

    user.roles.append(role)
    db_session.add(user)
    db_session.commit()


@users.command('revoke-role')
@click.argument('username')
@click.argument('role')
def revoke_role(username: str, role: str):
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        click.echo('No such user.')
        return

    role = db_session.query(Role).filter(Role.name == role).first()
    if not role:
        click.echo('No such role.')
        return

    user.roles.remove(role)
    db_session.add(user)
    db_session.commit()


@tools.command()
@click.option('--make-changes', is_flag=True, default=False)
def purge(make_changes=False):
    """
    Purges:

        - Projects with 0 events older than 24h.
        - Users with 0 projects older than 30 days.
    """
    projects = Project.query.filter(
        Project.message_count == 0,
        Project.created <= (
            datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        )
    )

    for project in projects:
        print(f'- [project] {project.name}')

        if make_changes:
            db_session.delete(project)

    if make_changes:
        db_session.commit()

    users_to_purge = User.query.filter(
        ~User.projects.any(),
        User.joined <= (
            datetime.datetime.utcnow() - datetime.timedelta(days=30)
        )
    )

    for user in users_to_purge:
        print(f'- [user] {user.username}')

        if make_changes:
            db_session.delete(user)

    if make_changes:
        db_session.commit()


@tools.command('add-role')
@click.argument('name')
def add_role(name: str):
    """
    Add a new user role.
    """
    role = db_session.merge(Role(name=name))
    db_session.add(role)
    db_session.commit()


@tools.command('add-permission')
@click.argument('name')
def add_permission(name: str):
    """
    Add a new role permission.
    """
    permission = db_session.merge(Permission(name=name))
    db_session.add(permission)
    db_session.commit()


@tools.command('add-default-roles')
def add_default_roles():
    admin: Role = db_session.merge(Role(name='admin'))
    superuser: Permission = db_session.merge(Permission(name='superuser'))

    admin.permissions.append(superuser)

    db_session.add(admin)
    db_session.commit()


@bots.command('start')
def bots_start():
    """
    Start the IRC bot manager.
    """
    from notifico.services.irc_bot import wait_for_events

    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(wait_for_events())


if __name__ == '__main__':
    cli()
