# -*- coding: utf8 -*-
import logging

from collections import defaultdict, deque

from utopia.client import CoreClient
from utopia.plugins import Plugin
from utopia.plugins.core import RegisterPlugin, PingPlugin


class NickRegisterPlugin(RegisterPlugin):
    """
    Keep trying incremental nicks until we find one that is free.
    """
    def __init__(self, *args, **kwargs):
        super(NickRegisterPlugin, self).__init__(*args, **kwargs)
        self._tries = 0

    def next_nick(self, client):
        self._tries += 1
        return 'Notifico-{0:03}'.format(self._tries)


class LoggingPlugin(Plugin):
    """
    Log all _incoming_ IRC messages.
    """
    def __init__(self, *args, **kwargs):
        super(LoggingPlugin, self).__init__(*args, **kwargs)
        logging.basicConfig(
            filename='botifico.log',
            level=logging.DEBUG
        )

    def msg_not_handled(self, client, message):
        logging.debug('[{0}] {1!r}'.format(client.address, message))


class ChannelPlugin(Plugin):
    """
    Handle channel-wise events, such as joining or leaving.
    """
    def msg_join(self, client, message):
        client.joined_channel(message.args[0])

    def msg_kick(self, client, message):
        client.kicked_from_channel(message.args[0])


class Bot(CoreClient):
    def __init__(self, bot_state, *args, **kwargs):
        super(Bot, self).__init__(*args, **kwargs)
        self._bot_state = bot_state
        self._wait_to_send = defaultdict(deque)
        self._channels = set()
        self._joining = set()

        self.plugins.add(LoggingPlugin())
        self.plugins.add(NickRegisterPlugin('Notifico-000', 'Notifico'))
        self.plugins.add(PingPlugin())
        self.plugins.add(ChannelPlugin())

    def send_message(self, channel, message):
        """
        Sends `message` to `channel`, wraping as needed. If the bot is
        not already in `channel`, the message is queue'd and waits for the
        ``JOIN`` to complete.
        """
        # Ignore any newlines both for security, and because we'll handle
        # wordwrapping to compact long commits.
        message = message.replace('\n', ' ')
        channel = channel.lower()

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
        """
        The list of channels this bot currently occupies.
        """
        return self._channels

    def joined_channel(self, channel):
        """
        Called when the bot has successfully joined `channel`. Any
        queue'd messages waiting to go to this channel are sent and
        the queue deleted.
        """
        channel = channel.lower()
        self._channels.add(channel)
        self.bot_event('Joined channel.', 'join', 'ok', channel=channel)

        # Send any messages we were waiting to send.
        if channel in self._wait_to_send:
            waiting = self._wait_to_send[channel]
            while waiting:
                self.send_message(channel, waiting.popleft())
            del self._wait_to_send[channel]

    def left_channel(self, channel):
        """
        The bot has left a channel for some *good* reason.
        """
        self.bot_event('Left channel.', 'part', 'ok', channel=channel)
        self._remove_channel(channel)

    def kicked_from_channel(self, channel):
        """
        The bot was kicked from the channel.
        """
        self.bot_event(
            'Kicked from channel.',
            'kick',
            'warning',
            channel=channel
        )
        self._remove_channel(channel)

    def _remove_channel(self, channel):
        """
        Remove `channel` from the internal set.
        """
        self._channels.discard(channel.lower())

    def bot_event(self, *args, **kwargs):
        self._bot_state.bot_event(self, *args, **kwargs)
