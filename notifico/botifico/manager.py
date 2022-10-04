import asyncio
import dataclasses
from collections import defaultdict
from typing import Dict, Set, Type, Optional, Iterable

from notifico.botifico.bot import Network, Bot
from notifico.botifico.contrib.plugins.ready import ready_plugin
from notifico.botifico.logger import logger
from notifico.botifico.plugin import Plugin


@dataclasses.dataclass(frozen=True)
class Channel:
    name: str
    password: Optional[str] = None


class ChannelProxy:
    network: Network
    name: str
    bot: Bot

    def __init__(self, bot: Bot, network: Network, channel: Channel):
        self.bot = bot
        self.network = network
        self.channel = channel
        self.bot.register_handler('JOIN', self.on_join)

        self.joined = asyncio.Event()

    async def join(self, *, wait=True, timeout: int = 10):
        """
        JOINs the channel.
        """
        if self.joined.is_set():
            return

        logger.info(f'[manager] Waiting on ready status for {self.bot}')

        await asyncio.wait_for(
            ready_plugin.is_ready(self.bot).wait(),
            timeout=timeout
        )

        await self.bot.send('JOIN', self.channel.name)
        if wait:
            logger.info(
                f'[manager] Waiting on joined status for {self.bot}'
                f' on channel {self.channel!r}.'
            )
            await asyncio.wait_for(self.joined.wait(), timeout=timeout)

    async def private_message(self, message: str):
        await self.join()
        await self.bot.send('PRIVMSG', self.channel.name, f':{message}')

    async def notice(self, message: str):
        await self.bot.send('NOTICE', self.channel.name, f':{message}')

    async def on_join(self, args):
        if args[0].lower() == self.channel.name.lower():
            self.joined.set()


class ChannelBot(Bot):
    def __init__(self, manager: 'Manager', network: Network, **kwargs):
        super().__init__(network=network, **kwargs)
        self.channels = {}
        self.manager = manager

    def __getitem__(self, channel: Channel):
        # FIXME: This is missing the logic to handle 005 messages for channel
        #        limitations. Currently most networks limit you to 255 channels
        #        per connection, and we're nowhere close to that anywhere but
        #        irc.libera.chat.
        return self.channels.setdefault(
            channel,
            ChannelProxy(
                bot=self,
                network=self.network,
                channel=channel
            )
        )

    def task_exception(self, ex: Exception):
        try:
            self.manager.bots[self.network].remove(self)
        except KeyError:
            # We don't care if some other source has already removed us from
            # our manager's tracking set.
            pass


class Manager(Plugin):
    """
    A Manager is a high-level coordinator of one or more bots connect to one or
    more networks.

    .. note::

        The `Manager` will always enable the `ready_plugin`, as it's needed
        to enable channel support.
    """
    bots: Dict[Network, Set[ChannelBot]]
    bot_class: Type[Bot]

    def __init__(self, name, *, bot_class=ChannelBot):
        super().__init__(name)
        self.bot_class = bot_class
        self.bots = defaultdict(set)
        self.register_plugin(ready_plugin)

    def register_plugin(self, plugin: Plugin):
        """
        Registers a plugin, including all of its event handlers, with the
        Manager.
        """
        # Register for future bots.
        for key in plugin.event_receivers.keys():
            self.event_receivers[key].update(plugin.event_receivers[key])

        # Update existing bots.
        for bots in self.bots.values():
            for bot in bots:
                bot.register_plugin(plugin)

    async def bots_by_network(self, network: Network) -> Iterable[ChannelBot]:
        """
        Return all bots on the given network.

        If no bot is connected to the given network, one will be created and
        connected.
        """
        bots = self.bots[network]
        if not bots:
            bot = self.bot_class(self, network)
            bot.register_plugin(self)
            bots.add(bot)
            await bot.connect()

        return bots

    async def channel(self, network: Network, channel: Channel):
        """
        Return a :py:`Channel` for the given network.

        This will attempt to find a usable bot for the given channel,
        connecting one if necessary.
        """
        bots = await self.bots_by_network(network)
        for bot in bots:
            return bot[channel]
