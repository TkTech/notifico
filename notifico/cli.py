import datetime

import click
from rich.console import Console
from flask.cli import FlaskGroup
from rich.markup import escape
from sqlalchemy import func

from notifico import create_app, db
from notifico.models import Project
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
            db.session.delete(project)

    if make_changes:
        db.session.commit()

    users_to_purge = User.query.filter(
        ~User.projects.any(),
        User.joined <= (
            datetime.datetime.utcnow() - datetime.timedelta(days=30)
        )
    )

    for user in users_to_purge:
        print(f'- [user] {user.username}')

        if make_changes:
            db.session.delete(user)

    if make_changes:
        db.session.commit()


if __name__ == '__main__':
    cli()
