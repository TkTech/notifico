# -*- coding: utf8 -*-

from collections import deque
from functools import wraps, partial

from utopia import signals
from utopia.client import ProtocolClient
from utopia.plugins.protocol import ISupportPlugin


class BotificoBot(ProtocolClient):
    def __init__(self, identity, host, port=6667, ssl=False, plugins=None):
        plugins = plugins or []
        self._isupport = ISupportPlugin()
        plugins.append(self.isupport)
        ProtocolClient.__init__(self, identity, host, port, ssl, plugins)

        self._channels = dict()

    def send_message(self, channel, message):
        name = channel.channel.lower()

        if name not in self._channels:
            self._channels[name] = Channel(self, name)

        self._channels[name].join(channel.password)
        self._channels[name].message(message)

    def will_join(self, channel):
        prefix = channel.channel[0]
        # Maximum number of channels for channels with this prefix.
        channel_limit = self._isupport[1].get('CHANLIMIT', {}).get(prefix, 20)

        # Find all the channels we're already in with this prefix.
        channels = [c for c in self._channels if c[0] == prefix]
        if len(channels) >= channel_limit:
            return False

        return True


class Channel(object):
    def filter_channel(f):
        @wraps(f)
        def _f(self, client, prefix, target, args):
            if target.lower() == self.lname:
                f(self, client, prefix, target, args)
        return _f

    def __init__(self, client, name):
        self._client = client
        self._name = name

        self._joined = False
        self._message_queue = deque()

        signals.m.on_JOIN.connect(self.on_join, sender=client)

    @property
    def name(self):
        """
        Channel name.
        """
        return self.name

    @property
    def lname(self):
        """
        Channel name in lowercase.
        """
        return self.name.lower()

    @property
    def joined(self):
        """
        True if bot is currently in this channel.
        """
        return self._joined

    def join(self, password=None):
        """
        Attempt to join the channel.
        """
        if not self._joined:
            self._client.join_channel(self.lname, password)

    def _send_message(self, message, type_='PRIVMSG'):
        self._message_queue.append(
            (self._client.send, type_, self.name, message)
        )

        self._check_message_queue()

    message = partial(_send_message, type_='PRIVMSG')
    message.__doc__ = 'Send privmsg to this channel.'
    notice = partial(_send_message, type_='NOTICE')
    notice.__doc__ = 'Send notice to this channel.'

    @filter_channel
    def on_join(self, client, prefix, target, args):
        if prefix[0].lower() == client.identity.nick.lower():
            self._joined = True
            self._check_message_queue()

    @filter_channel
    def on_kick(self, client, prefix, target, args):
        if prefix[0].lower() == client.identity.nick.lower():
            self._joined = False

    def _check_message_queue(self):
        """
        Check the channel's message queue. If non-empty and joined,
        pop a message and send it.
        """
        while self._joined and self._message_queue:
            message = self._message_queue.popleft()
            message[0](*message[1:])
            # maybe gevent.sleep(interval)
