"""
The :py:`ready_plugin` implements a single event, `is_ready`, which is
triggered when the server is ready for non-handshake (NICK, USER, PASS, etc)
messages.

Ex:

.. code::python

    from notifico.botifico.bot import Bot, Network
    from notifico.botifico.contrib.plugins.identity import identity_plugin
    from notifico.botifico.contrib.plugins.ready import ready_plugin

    async def example():
        bot = Bot(Network('irc.libera.chat', 6697, True))
        bot.register_plugin(identity_plugin)
        bot.register_plugin(ready_plugin)

        await bot.connect()
        await ready_plugin.is_ready(bot).wait()
        await bot.send('JOIN', '#notifico')
"""
import asyncio

from notifico.botifico.bot import Bot
from notifico.botifico.events import Event
from notifico.botifico.logger import logger
from notifico.botifico.plugin import Plugin


class ReadyPlugin(Plugin):
    def is_ready(self, bot: Bot):
        is_ready = self.get(bot, 'is_ready')
        if is_ready is None:
            is_ready = asyncio.Event()
            self.set(bot, 'is_ready', is_ready)

        return is_ready


ready_plugin = ReadyPlugin(__name__)


@ready_plugin.on(Event.RPL_ENDOFMOTD)
@ready_plugin.on(Event.ERR_NOMOTD)
async def on_motd(bot: Bot, plugin: ReadyPlugin):
    plugin.is_ready(bot).set()
    logger.info(f'[ready_plugin] bot {bot} marked as ready.')
