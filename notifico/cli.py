import asyncio
import logging
import datetime
from pathlib import Path
from typing import List

import click
from flask.cli import FlaskGroup
from sqlalchemy import update, delete

from notifico import create_app
from notifico.database import db_session, Base, engine
from notifico.models import (
    Project,
    Role,
    Permission,
    IRCNetwork,
    Channel,
    NetworkEvent,
)
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


@cli.group()
def irc():
    """IRC utility commands."""


@users.command()
@click.argument("username")
@click.argument("email")
@click.password_option()
def create(username, email, password):
    """
    Create a new user.
    """
    user = User.new(username, email, password)
    db_session.add(user)
    db_session.commit()


@users.command("grant-role")
@click.argument("username")
@click.argument("role")
def grant_role(username: str, role: str):
    """
    Grants a user a specific role. Does nothing if the user already has the
    role.
    """
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        click.echo("No such user.")
        return

    role = db_session.query(Role).filter(Role.name == role).first()
    if not role:
        click.echo("No such role.")
        return

    user.roles.append(role)
    db_session.add(user)
    db_session.commit()


@users.command("revoke-role")
@click.argument("username")
@click.argument("role")
def revoke_role(username: str, role: str):
    user = db_session.query(User).filter(User.username == username).first()
    if not user:
        click.echo("No such user.")
        return

    role = db_session.query(Role).filter(Role.name == role).first()
    if not role:
        click.echo("No such role.")
        return

    user.roles.remove(role)
    db_session.add(user)
    db_session.commit()


@tools.command()
@click.option("--make-changes", is_flag=True, default=False)
def purge(make_changes=False):
    """
    Purges:

        - Projects with 0 events older than 24h.
        - Users with 0 projects older than 30 days.
    """
    projects = Project.query.filter(
        Project.message_count == 0,
        Project.created
        <= (datetime.datetime.utcnow() - datetime.timedelta(hours=24)),
    )

    for project in projects:
        print(f"- [project] {project.name}")

        if make_changes:
            db_session.delete(project)

    if make_changes:
        db_session.commit()

    users_to_purge = User.query.filter(
        ~User.projects.any(),
        User.joined
        <= (datetime.datetime.utcnow() - datetime.timedelta(days=30)),
    )

    for user in users_to_purge:
        print(f"- [user] {user.username}")

        if make_changes:
            db_session.delete(user)

    if make_changes:
        db_session.commit()


@tools.command("add-role")
@click.argument("name")
def add_role(name: str):
    """
    Add a new user role.
    """
    role = db_session.merge(Role(name=name))
    db_session.add(role)
    db_session.commit()


@tools.command("add-permission")
@click.argument("name")
def add_permission(name: str):
    """
    Add a new role permission.
    """
    permission = db_session.merge(Permission(name=name))
    db_session.add(permission)
    db_session.commit()


@bots.command("start")
def bots_start():
    """
    Start the IRC bot manager.
    """
    from notifico.services.irc_bot import wait_for_events

    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(wait_for_events())


@irc.command("set-public")
@click.argument("network-id", type=int)
@click.argument("public", type=int)
def irc_set_public(network_id: int, public: int):
    """
    Sets the `public` value on a network
    """
    network: IRCNetwork = (
        db_session.query(IRCNetwork).filter(IRCNetwork.id == network_id).first()
    )

    if not network:
        click.echo("No such network.")
        return

    network.public = public
    if public > 0:
        # If a network is becoming global, it should no longer be associated
        # with a specific user.
        network.owner_id = None

    db_session.add(network)
    db_session.commit()


@irc.command("merge")
@click.argument("network-id", type=int)
@click.argument("other-network", nargs=-1, type=int)
def irc_merge(network_id: int, other_network: List[int]):
    """
    Merges the provided networks into `network_id`, and deletes the
    now-redundant networks.
    """
    network: IRCNetwork = (
        db_session.query(IRCNetwork).filter(IRCNetwork.id == network_id).first()
    )

    confirm = click.confirm(
        f"This will merge {other_network} into {network_id}."
    )
    if not confirm:
        return

    db_session.execute(
        update(Channel)
        .where(Channel.network_id.in_(other_network))
        .values(network_id=network.id)
    )

    db_session.execute(
        delete(NetworkEvent)
        .where(NetworkEvent.network_id == IRCNetwork.id)
        .where(IRCNetwork.id.in_(other_network))
        .execution_options(synchronize_session=False)
    )

    db_session.execute(
        delete(IRCNetwork).where(IRCNetwork.id.in_(other_network))
    )

    db_session.commit()


@tools.command("bootstrap")
def bootstrap_command():
    Base.metadata.create_all(engine)

    # then, load the Alembic configuration and generate the
    # version table, "stamping" it with the most recent rev:
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(str(Path(__file__).parent / ".." / "alembic.ini"))
    command.stamp(alembic_cfg, "head")

    # Add the default user roles.
    admin: Role = db_session.merge(Role(name="admin"))
    superuser: Permission = db_session.merge(Permission(name="superuser"))

    admin.permissions.append(superuser)

    db_session.add(admin)
    db_session.commit()


if __name__ == "__main__":
    cli()
