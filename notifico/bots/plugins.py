# -*- coding: utf8 -*-
from notifico.utopia import signals
import datetime


class NickInUsePlugin(object):
    def __init__(self, nick_func):
        """
        A plugin that automatically tries the next nick, if
        the current nick is already in use.

        :param nick_func: A function which returns
                          the new nick to select
        """
        self._fun = nick_func

    def bind(self, client):
        signals.m.on_433.connect(self.on_433, sender=client)

        return self

    def on_433(self, client, prefix, target, args):
        client.identity._nick = self._fun()

        client.send('NICK', client.identity.nick)
        client.send(
            'USER',
            client.identity.user,
            '8',
            '*',
            client.identity.real
        )


class CTCPPlugin(object):
    def __init__(self, ctcp_responses=None, default=None):
        """
        A plugin which automatically responds to CTCP queries.
        The plugin requires a ProtocolClient.

        :param ctcp_responses: A dictionary containing key, value pairs,
                               the key being the CTCP tag and the value
                               being the answer. The value can be a callable
                               which takes the tag and the argument as argument.
        :param default: A default answer for a non-existent CTCP-request.
                        This can also be a callable (see ctcp_responses).
        """
        self.ctcp_responses = ctcp_responses
        if self.ctcp_responses is None:
            self.ctcp_responses = dict()

        self.default = default

    def bind(self, client):
        signals.m.on_CTCP.connect(self.on_ctcp, sender=client)

        return self

    def on_ctcp(self, client, prefix, target, tag, args):
        reply = self.ctcp_responses.get(tag, self.default)
        if reply is None:
            return

        if callable(reply):
            reply = reply(tag, args)

        client.ctcp_reply(prefix[0], [(tag, reply)])

    @staticmethod
    def ctcp_ping(tag, arg):
        return arg

    @staticmethod
    def ctcp_time(tag, arg):
        return datetime.datetime.now().isoformat(' ')
