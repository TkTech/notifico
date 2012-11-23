# -*- coding: utf8 -*-
from utopia.plugins import Plugin
from utopia.errors import IRCError


class RegisterPlugin(Plugin):
    """
    Handles registering with the server upon connection, and handles
    responses associated with PASS, NICK, and USER.
    """
    def __init__(self, nickname, username, password=None, realname=None,
        visible=False):
        self._original_nickname = nickname
        self._original_username = username
        self._original_password = password
        self._original_realname = realname or nickname
        self._visible = visible

    def event_connected(self, client):
        client.send('USER', [
            self._original_username,
            '0' if self._visible else '8',
            '*',
            self._original_realname
        ], c=True)
        client.send('NICK', [self._original_nickname])

    def msg_001(self, client, message):
        client.user.nickname = message.args[0]
        client.user.realname = self._original_realname
        client.user.username = self._original_username

    def msg_433(self, client, message):
        # ERR_NICKNAMEINUSE
        next_nick = self.next_nick(client)
        client.send('NICK', [next_nick])

    def next_nick(self, client):
        raise IRCError('Nick in use or invalid')
