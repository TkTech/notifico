# -*- coding: utf8 -*-
__all__ = ('BotManager',)
import random
import logging
from collections import defaultdict

from utopia import signals
from utopia.client import Identity
from utopia.plugins.handshake import HandshakePlugin
from utopia.plugins.protocol import EasyProtocolPlugin
from utopia.plugins.util import LogPlugin

from notifico.bots.util import Network
from notifico.bots.plugins import NickInUsePlugin, CTCPPlugin
import notifico.config as config

logger = logging.getLogger(__name__)


class BotManager(object):
    """
    A BotManager creates and controls bots as needed to carry out
    the commands it is given.
    """
    def __init__(self, bot_class):
        self._active_bots = defaultdict(set)
        self._bot_class = bot_class

        # A stack of released nicknames to keep our nicknames
        # unique across all networks.
        self._nick_stack = []

        self._ctcp_responses = {
            'PING': CTCPPlugin.ctcp_ping,
            'TIME': CTCPPlugin.ctcp_time,
            'VERSION': 'Notifico! - https://github.com/notifico/notifico'
        }

    @property
    def active_bots(self):
        """
        A mapping of networks and the bots currently active
        on them.
        """
        return self._active_bots

    def send_message(self, network, channel, message):
        """
        Send the given `message` to `channel` on `network`.
        """
        # Find all of the bots active on the given network.
        bot = self.find_bot_for_channel(network, channel)

        if bot is None:
            # For some reason we were unable to find a bot
            # able to send to this channel.
            return False

        return bot.send_message(channel, message)

    def find_bot_for_channel(self, network, channel):
        """
        Find (or create) a bot able to send to `channel` on `network`.
        """
        network_bots = self.find_bots_for_network(network)
        if not network_bots:
            # There aren't any bots currently active on this network,
            # so create one.
            return self._create_bot(network)

        # There are some bots already on this network, try to find
        # a free one, and if none are willing (ex: maximum channels)
        # create a new one.
        for bot in network_bots:
            if bot.will_join(channel):
                return bot
        else:
            return self._create_bot(network)

    def find_bots_for_network(self, network):
        """
        Returns all of the bots active on `network`.
        """
        return self._active_bots[network._replace(ssl=False)]

    def _create_bot(self, network):
        """
        Create, register, and return a new bot for `network`.
        """
        nickname = self.free_nick()
        bot = self._bot_class(
            Identity(
                nickname,
                user=config.IRC_USERNAME,
                real=config.IRC_REALNAME,
                password=network.password
            ),
            network.host,
            port=network.port,
            ssl=network.ssl,
            plugins=[
                EasyProtocolPlugin(),
                HandshakePlugin(),
                NickInUsePlugin(self.free_nick),
                CTCPPlugin(self._ctcp_responses),
                LogPlugin(logger=logging.getLogger(
                    '({0}:{1}:{2})'.format(*network)
                ))
            ]
        )
        try:
            bot.connect()
        except Exception:
            logger.error(
                'An issue occured while connecting to a host',
                exc_info=True,
                extra={
                    'data': {
                        'host': network.host,
                        'port': network.port,
                        'ssl': network.ssl,
                        'password': network.password
                    }
                }
            )
            return None

        signals.on_disconnect.connect(self.remove_bot, sender=bot)
        self._active_bots[network._replace(ssl=False)].add(bot)
        return bot

    def free_nick(self, suffix_length=4):
        """
        Returns a randomly generated nickname to use for client
        registration. Keeps track of which nicks are already in use globally.

        :param suffix_length: The maximum length for the randomly generated
                              nickname suffix.
        """
        
        # Trying the default nickname
        primary_nick = config.IRC_NICKNAME
        if primary_nick not in self._nick_stack:
            self._nick_stack.append(primary_nick)
            return primary_nick

        # Keep trying until we get a nickname that's not already in use.
        while True:
            new_nick = config.IRC_NICKNAME + '-{random_suffix:x}'.format(
                # By far the fastest pure-python method for a short hex
                # identifier.
                random_suffix=random.randrange(
                    16**suffix_length
                )
            )

            if new_nick not in self._nick_stack:
                break

        self._nick_stack.append(new_nick)
        return new_nick

    def give_up_nick(self, nickname):
        """
        A retiring bot is giving its nick up.
        """
        self._nick_stack.remove(nickname)

    def remove_bot(self, client):
        signals.on_disconnect.disconnect(self.remove_bot, sender=client)

        network = Network.from_client(client)._replace(ssl=False)

        if network not in self._active_bots:
            logger.debug(
                'Tried to remove a network that wasn\'t active.'
            )
            return

        self._active_bots[network].discard(client)
