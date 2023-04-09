"""
The py:`ping_plugin` simply replies to PINGs with a PONG command.
"""
from notifico.botifico.bot import Bot
from notifico.botifico.logger import logger
from notifico.botifico.plugin import Plugin


ping_plugin = Plugin(__name__)


@ping_plugin.on("PING")
async def on_ping(bot: Bot, args):
    """
    On a `PING`, reply with a `PONG`.
    """
    await bot.send("PONG", *args)
    logger.debug("[ping_plugin] PONGd a PING")
