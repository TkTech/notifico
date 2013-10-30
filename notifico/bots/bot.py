# -*- coding: utf8 -*-
__all__ = ('BotificoBot',)
from collections import deque

from utopia.basic import BasicClient


class BotificoBot(BasicClient):
    def __init__(self, manager, *args, **kwargs):
        BasicClient.__init__(self, *args, **kwargs)
        self._manager = manager
        self._messages = deque()

        self.on_bad_nick.connect(self.on_nick_conflict, sender = self)
        self.on_disconnect.connect(self._on_disconnect, sender = self)

    @property
    def manager(self):
        return self._manager

    def send_message(self, channel, message):
        password = channel.password
        channel = channel.channel
        _channel = self.ext.channels[channel]

        if not _channel.joined:
            _channel.join()

        # TODO: add message queue
        _channel.msg(message)

    def can_send_to_channel(self, channel):
        channel = channel.channel
        channel_limit = 40 # TODO: fetch real value

        channel = self.ext.channels[channel]
        if channel.joined or len(self.ext.channels.channels) < channel_limit:
            return True
        else:
            return False

    @staticmethod
    def on_nick_conflict(sender):
        return self.manager.free_nick()

    @staticmethod
    def _on_disconnect(sender, error):
        """
        The client has been disconnected, for any reason. Usually occurs
        on a network error.
        """

        sender.manager.give_up_nick(sender.nickname)
        sender.manager.remove_bot(sender)
