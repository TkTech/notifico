__all__ = ('get_plugins', 'get_plugin')
import functools
from importlib.metadata import entry_points


@functools.cache
def get_plugins():
    """
    Return a list of all installed plugins.
    """
    plugins = entry_points()['notifico_plugin']
    return [plugin.load() for plugin in plugins]


@functools.cache
def get_plugin(plugin_id):
    """
    Return a particular plugin.
    """
    for plugin in get_plugins():
        if plugin.PLUGIN_ID == plugin_id:
            return plugin
