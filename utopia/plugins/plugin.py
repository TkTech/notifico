# -*- coding: utf8 -*-
__all__ = ('Plugin', 'PluginList')
import gevent


class PluginList(object):
    def __init__(self, client):
        self.client = client
        self.plugins = []

    def add(self, plugin):
        self.plugins.append(plugin)

    def remove(self, plugin):
        self.plugins.remove(plugin)

    def remove_by_type(self, plugin):
        """
        Removes all `Plugins` of type `plugin`.
        """
        self.plugins[:] = [
            p for p in self.plugins if not isinstance(p, plugin)
        ]


class Plugin(object):
    def event_connected(self, client):
        """
        Called when the client has connected to a remote server.
        """

    def event_closing(self, client):
        """
        Called when the client connecting is closing.
        """

    def msg_not_handled(self, client, message):
        """
        Called whenever a message was recieved that was not handled
        by this Plugin.
        """

    def later(self, seconds, func, *args, **kwargs):
        """
        Proxy to gevent.spawn_later.
        """
        gevent.spawn_later(seconds, func, *args, **kwargs)
