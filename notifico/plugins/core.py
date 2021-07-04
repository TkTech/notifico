"""
Basic Plugin interface used to extend Notifico.
"""
__all__ = ('Plugin', 'PluginMetadata')

import dataclasses
from importlib.metadata import entry_points


@dataclasses.dataclass
class PluginMetadata:
    #: Explain what this plugin does.
    description: str
    #: The version of the plugin in use.
    version: str
    #: URL for this project, usually a source code repository.
    url: str
    #: Who created this plugin.
    author: str
    #: Contact address for this plugin.
    author_email: str = None


def all_available_plugins():
    """
    Returns a all available plugins, regardless of installation state or if
    they're disabled.
    """
    return {
        plugin.name: plugin.load()
        for plugin in entry_points()['notifico_plugin']
    }


class Plugin:
    """
    The base class for all Notifico plugins.

    Plugins can currently register new blueprints (aka views) and add new
    Channel providers.
    """
    @classmethod
    def metadata(cls) -> PluginMetadata:
        """
        Returns metadata about this plugin. Typically this information will
        only be visible in the Admin panel.
        """
        raise NotImplementedError()

    @classmethod
    def on_install(cls):
        """Called when a plugin is installed."""

    @classmethod
    def on_uninstall(cls):
        """Called when a plugin is uninstalled."""

    @classmethod
    def supports_groups(cls):
        """
        `True` if you want Notifico to present a Group add/remove widget to
        admins editing the plugin.

        Custom plugins may do whatever they wish with these groups. Source
        and Channel plugins use it to hide themselves except from approved
        groups.
        """
        return True

    @classmethod
    def admin_form(cls):
        """
        An optional FlaskForm *class* (not an instance!) that will be
        presented to an adminstrator when configuring global plugin settings.
        """

    @classmethod
    def config_from_form(cls, form):
        """
        Pack a configuration form into a dictionary. The returned dictionary
        must be safe to serialize as JSON.

        .. note::

            The default implementation is good for most simple forms. If you
            have a complex form, such as custom types or recursive forms,
            you might have to implement this.
        """
        return dict(
            (field.id, field.data) for field in form
            if field.id != 'csrf_token'
        )

    @classmethod
    def update_form_with_config(cls, form, config):
        """
        Update the provided form instance using the stored configuration
        in `config`.

        .. note::

            The default implementation is good for most simple forms. If you
            have a complex form, such as custom types or recursive forms,
            you might have to implement this.
        """
        if config is None or not isinstance(config, dict):
            return

        for field in form:
            if field.id in config:
                field.data = config[field.id]

    @classmethod
    def icon(cls) -> str:
        """
        The Font-Awesome (free) icon that should be used to identify this
        Plugin in the admin panel, if any is suitable.

        .. note::

            Don't add font-awesome modifiers like 'fa-fw', leave that up
            to themes.
        """
        return 'fas fa-question'

    @classmethod
    def register_channel(cls):
        """
        Returns a :class:`~notifico.plugins.channel:Channel` implementation
        provided by this plugin. Return value should be classes themselves,
        and *not an instance* of that class.

        .. note::

            Channels are 1:1 with plugins. Want to add two channels, add two
            plugins. This requirement may be relaxed in the future.
        """
        raise NotImplementedError()

    @classmethod
    def register_blueprints(cls):
        """
        Return a list of Flask blueprints to be registered with the main
        Notifico app.

        .. note::

            These blueprints will all 404 unless the plugin is also enabled
            from the admin panel.
        """
        raise NotImplementedError()
