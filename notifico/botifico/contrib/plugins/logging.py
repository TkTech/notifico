"""
The :py:`log_plugin` provides a simple way log messages received by a bot,
generally to support debugging.
"""
import logging

from notifico.botifico.events import Event
from notifico.botifico.logger import logger
from notifico.botifico.plugin import Plugin

log_plugin = Plugin(__name__)


@log_plugin.on(Event.on_message)
async def on_log(command, args, prefix):
    logger.debug(f'[log_plugin][{command}][{prefix} {args}')
