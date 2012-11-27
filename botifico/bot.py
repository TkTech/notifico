# -*- coding: utf8 -*-
from collections import defaultdict, deque

from utopia.client import CoreClient
from utopia.plugins import Plugin
from utopia.plugins.core import RegisterPlugin, PingPlugin


class NickRegisterPlugin(RegisterPlugin):
    def __init__(self, *args, **kwargs):
        super(NickRegisterPlugin, self).__init__(*args, **kwargs)
        self._tries = 0

    def next_nick(self, client):
        self._tries += 1
        return 'Notifico-{0:03}'.format(self._tries)


class LoggingPlugin(Plugin):
    def msg_not_handled(self, client, message):
        print('[{0}] {1!r}'.format(client.address, message))


class JoinedChannelPlugin(Plugin):
    def msg_join(self, client, message):
        client.joined_channel(message.args[0])


class Bot(CoreClient):
    def __init__(self, *args, **kwargs):
        super(Bot, self).__init__(*args, **kwargs)
        self._wait_to_send = defaultdict(deque)
        self._channels = set()
        self._joining = set()

        self.plugins.add(LoggingPlugin())
        self.plugins.add(NickRegisterPlugin('Notifico-000', 'Notifico'))
        self.plugins.add(PingPlugin())
        self.plugins.add(JoinedChannelPlugin())

    def send_message(self, channel, message):
        # Ignore any line formatting both for security, and because
        # we'll handle the wordwrap.
        message = message.replace('\n', ' ')

        # 7 (PRIVMSG) + 1 (space) + <channel> + 2 (space :) + 2 (\r\n)
        prefix_length = 12 + len(channel)

        if len(message) + prefix_length >= 512:
            # The total message exceeds IRC's mandatory 512 byte limit.
            max_chunk = 512 - prefix_length
            for i in xrange(0, len(message), max_chunk):
                self._send_message(channel, message[i:i + max_chunk])
        else:
            # Our message is small enough to fit in a single PRIVMSG.
            self._send_message(channel, message)

    def _send_message(self, channel, message):
        if channel not in self._channels:
            # Queue the message to send after we've joined this channel.
            self._wait_to_send[channel].append(message)
            # Make sure we aren't already trying to join this channel
            if channel not in self._joining:
                self.send('JOIN', [channel])
        else:
            # We're already in this channel, go ahead and directly send it.
            self.send('PRIVMSG', [channel, message], c=True)

    @property
    def channels(self):
        return self._channels

    def joined_channel(self, channel):
        self._channels.add(channel)

        # Send any messages we were waiting to send.
        if channel in self._wait_to_send:
            waiting = self._wait_to_send[channel]
            while waiting:
                self.send_message(channel, waiting.popleft())
            del self._wait_to_send[channel]
