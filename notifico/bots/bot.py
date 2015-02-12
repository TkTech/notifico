# -*- coding: utf8 -*-

from functools import wraps, partial

import gevent
import gevent.queue
import gevent.event

from utopia import signals
from utopia.client import ProtocolClient
from utopia.plugins.protocol import ISupportPlugin
from utopia.plugins.util import LogPlugin


class BotificoBot(ProtocolClient):
    def __init__(self, identity, host, port=6667, ssl=False, plugins=None):
        self._isupport = ISupportPlugin()
        plugins = plugins or []
        plugins.append(self._isupport)

        ProtocolClient.__init__(self, identity, host, port, ssl, plugins)

        self.message_min_delay = 1.5

        self._ready = False
        self._channels = dict()

        signals.on_registered.connect(self.on_ready, sender=self)

    @property
    def ready(self):
        """
        Is the client fully connected and can accept commands like JOIN.
        """
        return self._ready

    def send_message(self, channel, message):
        """
        Sends a privmsg message to a channel.
        """
        name = channel.channel.lower()

        if name not in self._channels:
            self._channels[name] = Channel(self, name, channel.password)
            self._channels[name].message_min_delay = self.message_min_delay

        self._channels[name].message(message)

    def will_join(self, channel):
        """
        Returns True if this bot can join this channel.
        """
        prefix = channel.channel[0]
        # Maximum number of channels for channels with this prefix.
        channel_limit = self._isupport[1].get('CHANLIMIT', {}).get(prefix, 20)

        # Find all the channels we're already in with this prefix.
        channels = [c for c in self._channels if c[0] == prefix]
        if len(channels) >= channel_limit:
            return False

        return True

    def on_ready(self, client):
        # no need to disconnect the event, on_registered fires only once
        self._ready = True

        # join the channels we have messages for,
        # but we couldn't join yet
        for name, channel in self._channels.items():
            if not channel.joined:
                channel.join()


class Channel(object):
    def filter_channel(f):
        @wraps(f)
        def _f(self, client, prefix, target, args):
            if target.lower() == self.lname:
                f(self, client, prefix, target, args)
        return _f

    def __init__(self, client, name, password=None):
        self._client = client
        self._name = name
        self._password = password

        self.message_min_delay = 0

        self._joined = gevent.event.Event()
        self._message_queue = gevent.queue.Queue()

        signals.m.on_JOIN.connect(self.on_join, sender=client)
        signals.m.on_KICK.connect(self.on_kick, sender=client)

        # start off the sender greenlet
        gevent.spawn(self._check_message_queue)

    @property
    def name(self):
        """
        Channel name.
        """
        return self._name

    @property
    def lname(self):
        """
        Channel name in lowercase.
        """
        return self._name.lower()

    @property
    def joined(self):
        """
        True if bot is currently in this channel.
        """
        return self._joined.is_set()

    def join(self):
        """
        Attempt to join the channel.
        """
        if not self.joined and self._client.ready:
            self._client.join_channel(self.lname, self._password)
            return True
        return False

    def _send_message(self, func, message):
        # this should not block anyways, since the queue size
        # is unlimited
        self._message_queue.put_nowait(
            (func, self.name, message)
        )

    def message(self, message):
        """
        Sends a privmsg to this channel.
        """
        return self._send_message(self._client.privmsg, message)

    def notice(self, message):
        """
        Sends a notice to this channel.
        """
        return self._send_message(self._client.notice, message)

    @filter_channel
    def on_join(self, client, prefix, target, args):
        if prefix[0].lower() == client.identity.nick.lower():
            self._joined.set()

    @filter_channel
    def on_kick(self, client, prefix, target, args):
        if args[0].lower() == client.identity.nick.lower():
            self._joined.clear()

    def _check_message_queue(self):
        """
        Check the channel's message queue. If non-empty and joined,
        sends all messages.
        """
        # wait for a message
        message = self._message_queue.get()
        self.join()
        # there is a message, but the channel might not
        # be joined yet (this will not block if we are already in the channel)
        self._joined.wait()
        # send the message
        message[0](*message[1:])

        gevent.spawn_later(self.message_min_delay, self._check_message_queue)
