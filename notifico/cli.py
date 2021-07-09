import click
from flask.cli import FlaskGroup
from rich.console import Console
from rich.table import Table

from notifico.app import create_app
from notifico.extensions import db
from notifico.models.plugin import Plugin
from notifico.plugins.core import all_available_plugins


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


@cli.group('plugins')
def plugins():
    """Commands used for plugin management."""


@plugins.command('list')
def plugins_list():
    """List all available plugins."""
    from notifico.plugins.core import all_available_plugins
    from notifico.models.plugin import Plugin

    console = Console()

    table = Table(show_header=True)
    table.add_column('plugin_id')
    table.add_column('Installed', justify='center')
    table.add_column('Enabled', justify='center')
    table.add_column('URL')
    table.add_column('Description')

    for plugin_id, plugin in all_available_plugins().items():
        metadata = plugin.metadata()
        record = Plugin.query.filter_by(plugin_id=plugin_id).first()
        table.add_row(
            plugin_id,
            '\u2713' if record else '\u2717',
            '\u2713' if record and record.enabled else '\u2717',
            metadata.url,
            metadata.description
        )

    console.print(table)


@plugins.command('install')
@click.argument('plugin_id')
@click.option(
    '--enable',
    is_flag=True,
    help='Enable this plugin after installing'
)
def plugins_install(plugin_id, enable=False):
    """Install the plugin specified by `plugin_id`."""
    from notifico.models.group import Group, CoreGroups

    plugin = all_available_plugins().get(plugin_id)
    if plugin is None:
        click.echo(f'No plugin found by the name of {plugin_id}')
        return 1

    record = Plugin.query.filter_by(plugin_id=plugin_id).first()
    if record:
        click.echo('This plugin is already installed.')
        return

    db.session.add(
        Plugin(
            plugin_id=plugin_id,
            enabled=enable,
            groups=[
                db.session.query(Group).get(CoreGroups.REGISTERED.value)
            ]
        )
    )
    db.session.commit()
    plugin.on_install()
    click.echo('Plugin has been installed.')


@plugins.command('uninstall')
@click.argument('plugin_id')
def plugins_uninstall(plugin_id):
    """Uninstall the plugin specified by `plugin_id`.

    If you want to keep plugin data, you should just disable it instead.
    """
    plugin = all_available_plugins().get(plugin_id)
    if plugin is None:
        click.echo(f'No plugin found by the name of {plugin_id}')
        return 1

    record = Plugin.query.filter_by(plugin_id=plugin_id).first()
    if record is None:
        click.echo('This plugin is not installed.')
        return

    yes = click.confirm(
        'This plugin will be uninstalled, potentially permanently deleting'
        ' all associated data. Are you sure?'
    )
    if yes:
        db.session.delete(record)
        db.session.commit()
        plugin.on_uninstall()
        click.echo('Plugin has been uninstalled.')


@plugins.command('enable')
@click.argument('plugin_id')
def plugins_enable(plugin_id, enable=False):
    """Enable the given plugin."""
    plugin = all_available_plugins().get(plugin_id)
    if plugin is None:
        click.echo(f'No plugin found by the name of {plugin_id}')
        return 1

    record = Plugin.query.filter_by(plugin_id=plugin_id).first()
    if record is None:
        click.echo(
            f'This plugin is not installed yet. Install and enable it with'
            f' "notifico plugin install {plugin_id} --enable"'
        )
        return

    record.enabled = True
    db.session.commit()


@plugins.command('disable')
@click.argument('plugin_id')
def plugins_disable(plugin_id, enable=False):
    """Disable the given plugin."""
    plugin = all_available_plugins().get(plugin_id)
    if plugin is None:
        click.echo(f'No plugin found by the name of {plugin_id}')
        return 1

    record = Plugin.query.filter_by(plugin_id=plugin_id).first()
    if record is None:
        click.echo(
            f'This plugin is not installed yet. Install it with'
            f' "notifico plugin install {plugin_id}"'
        )
        return

    record.enabled = False
    db.session.commit()
