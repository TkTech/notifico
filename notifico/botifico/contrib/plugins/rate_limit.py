"""
The :py:`rate_limit_plugin` provides a simple way rate limit sending messages.
"""
import asyncio
import random
import time

from notifico.botifico.bot import Bot
from notifico.botifico.events import Event
from notifico.botifico.logger import logger
from notifico.botifico.plugin import Plugin


rate_limit_plugin = Plugin(__name__)


@rate_limit_plugin.on(Event.on_write, block=True)
async def on_write(bot: Bot):
    time_between_messages = rate_limit_plugin.get(
        bot,
        'time_between_messages',
        1
    )
    last_message = rate_limit_plugin.get(bot, 'last_message', 0)

    # We don't have to do anything fancy here, since there's no way for
    # something to write unless it ignored our API and just wrote to the
    # socket.
    now = time.monotonic()

    if now < last_message + time_between_messages:
        how_long = last_message + time_between_messages - now
        logger.debug(
            f'[rate_limit_plugin] Sleeping for {how_long} seconds to comply'
            ' with rate limit requirements.'
        )
        await asyncio.sleep(
            (last_message + time_between_messages - now) + random.randint(
                0, time_between_messages * 2
            )
        )

    rate_limit_plugin.set(bot, 'last_message', time.monotonic())
