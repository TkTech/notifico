# -*- coding: utf8 -*-
__all__ = ('BotificoBot',)
from collections import deque

from utopia import Client, client_queue


class BotificoBot(Client):
    def __init__(self, manager, *args, **kwargs):
        super(BotificoBot, self).__init__(*args, **kwargs)
        self._manager = manager
        self._messages = deque()
        self._ready = False

    @property
    def manager(self):
        return self._manager

    @client_queue
    def send_message(self, channel, message):
        yield (self._send_message, channel, message)

    def _send_message(self, channel, message):
        c = self[channel.channel]
        c.join()
        c.send(message)

    def message_not_handled(self, client, message):
        print(message)

    def next_nickname(self):
        return self.manager.free_nick()

    def event_ready(self, client):
        self._ready = True

    def will_join(self, channel):
        prefix = channel[0]
        # Maximum number of channels for channels with this prefix.
        channel_limit = self.channel_limit(prefix=prefix, default=20)

        # Find all the channels we're already in with this prefix.
        channels = list(self.channels_by_prefix(prefix=prefix))
        if len(channels) >= channel_limit:
            return False

        return True

    def message_privmsg(self, client, message):
        # Stop PRIVMSG from going to message_not_handled
        pass

    def event_disconnected(self):
        """
        The client has been disconnected, for any reason. Usually occurs
        on a network error.
        """
        self.manager.give_up_nick(self.account.nickname)
        self.manager.remove_bot(self)
