import asyncio
import dataclasses
from collections import defaultdict
from typing import Dict, Set, Type, Optional, Iterable

from notifico.botifico.bot import Network, Bot
from notifico.botifico.contrib.plugins.ready import ready_plugin
from notifico.botifico.events import Event
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

        if self.channel.password:
            await self.bot.send(
                'JOIN',
                self.channel.name,
                # We sanitize long, long before this point, but just in case...
                self.channel.password.replace('\n', '')
            )
        else:
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

    def get_channel(self, channel: str) -> ChannelProxy | None:
        for channel_proxy in self.channels.values():
            if channel_proxy.channel.name == channel:
                return channel_proxy

    async def task_exception(self, ex: Exception):
        try:
            self.manager.bots[self.network].remove(self)
        except KeyError:
            # We don't care if some other source has already removed us from
            # our manager's tracking set.
            pass

        await super().task_exception(ex)


class Manager(Plugin):
    bots: Dict[Network, Set[ChannelBot]]
    bot_class: Type[Bot]

    def __init__(self, name: str, *, bot_class: Type[ChannelBot] = ChannelBot):
        """
        A Manager is a high-level coordinator of one or more bots connected to
        one or more networks.
        
        .. note::
    
            The `Manager` will always enable the `ready_plugin`, as it's needed
            to enable channel support.

        :param name: A unique name for the bot, shared across all its instances.
                     Used for namespacing.
        :param bot_class: An optional alternative class to use instead of
                          :class:`ChannelBot`
        """
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
        Return all bots connected (or connecting) to the given network.

        If no bot is connected to the given network, one will be created and
        connected.

        .. note::

            Any newly created bot is connected _asynchronously_, and may not
            be done by the time it's returned.

        :param network: The Network to search for.
        """
        bots = self.bots[network]
        
        # If there's no bots at all, just assume we need to connect one.
        if not bots:
            bot = await self.add_bot_to_network(network)
            asyncio.create_task(bot.connect())
            return [bot]

        return bots

    async def add_bot_to_network(self, network: Network) -> ChannelBot:
        """
        Add a bot to the given :class:`Network`, but does not attempt to
        connect it.

        :param network: The Network associated with the new bot.
        """
        bot = self.bot_class(self, network)
        bot.register_plugin(self)
        bot.register_handler(Event.on_disconnect, self.on_disconnect)
        self.bots[network].add(bot)
        return bot

    async def channel(self, network: Network, channel: Channel) -> ChannelProxy:
        """
        Return a :py:`ChannelProxy` for a bot connected to the given network.
        If no bot is connected, one will be connected for you.

        :param network: The Network to search for the channel.
        :param channel: The Channel to return.
        """
        bots = list(await self.bots_by_network(network))
        for bot in bots:
            if channel in bot.channels:
                return bot[channel]

        # TODO: Check to see if the bot is at the channel cap per connection
        #       (which comes from capabilities listed in 005), and create a
        #       new connection if it is.
        return bots[-1][channel]

    async def on_disconnect(self, bot: ChannelBot):
        """
        Event handler called whenever a bot is disconnected from the network.

        :param bot: The bot disconnecting.
        """
        try:
            self.bots[bot.network].remove(bot)
        except KeyError:
            # In the very rare chance something else has already removed us
            # (such as an exception occurring while handling disconnect), we
            # don't really care.
            pass

        logger.info(f'[manager] Bot disconnected cleanly {bot}')
