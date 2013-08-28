# -*- coding: utf8 -*-
__all__ = ('BotManager',)
import logging
from collections import defaultdict, namedtuple

from utopia import Account

logger = logging.getLogger(__name__)
Channel = namedtuple('Channel', ['channel', 'password'])


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
        self._max_nick = 0

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
            self,
            Account.new(
                nickname=nickname,
                username=u"notifico",
                realname=u"Notifico! - http://n.tkte.ch/"
            ),
            network
        )
        try:
            bot.connect()
        except Exception:
            logger.error(
                'An issue occured connection to a host',
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

        self._active_bots[network._replace(ssl=False)].add(bot)
        return bot

    def free_nick(self):
        """
        Return a free nickname to try.
        """
        if self._nick_stack:
            # A previously used nick that has been free'd is available.
            return self._nick_stack.pop()

        self._max_nick += 1
        return 'Not-{0:03}'.format(self._max_nick)

    def give_up_nick(self, nickname):
        """
        A retiring bot is giving its nick up.
        """
        self._nick_stack.append(nickname)

    def remove_bot(self, client):
        network = client.network._replace(ssl=False)

        if network not in self._active_bots:
            return

        self._active_bots[network].discard(client)
