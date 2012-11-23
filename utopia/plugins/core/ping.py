# -*- coding: utf8 -*-
__all__ = ('PingPlugin',)
from utopia.plugins import Plugin


class PingPlugin(Plugin):
    def msg_ping(self, client, message):
        client.send('PONG', message.args)
