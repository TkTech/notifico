"""
The :py:`identity_plugin` provides a simple implementation of a connection's
"identity". This means it handles:

    - setting the initial nickname, username, and realname
    - handling nickname conflicts
    -
"""
import secrets

from notifico.botifico.bot import Bot
from notifico.botifico.events import Event
from notifico.botifico.logger import logger
from notifico.botifico.plugin import Plugin


identity_plugin = Plugin(__name__)


@identity_plugin.on(Event.on_connected)
async def on_connected(bot: Bot, plugin: Plugin):
    nickname = plugin.get(bot, 'nickname', 'botifico')
    username = plugin.get(bot, 'username', 'botifico')
    realname = plugin.get(bot, 'realname', 'botifico')

    logger.debug(
        f'[identity_plugin] Attempting to identify {bot} with {nickname=},'
        f' {username=}, {realname=}.'
    )

    await bot.send('NICK', nickname)
    await bot.send('USER', username, '8', '*', f':{realname}')


@identity_plugin.on('433')
async def on_nickname_in_use(bot: Bot, plugin: Plugin):
    """
    Handle a NICK collision.
    """
    new_nickname = plugin.get(bot, 'backup_nickname')

    # If we couldn't get a backup nickname, take the current nickname and add
    # a random hex string.
    if new_nickname is None:
        new_nickname = (
            f'{plugin.get(bot, "nickname", "botifico")}'
            f'-{secrets.token_hex(4)}'
        )

    await bot.send('NICK', new_nickname)
