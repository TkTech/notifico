# -*- coding: utf8 -*-
__all__ = ('User',)


class User(object):
    def __init__(self, client):
        self._client = client
        self._nickname = None
        self._username = None
        self._realname = None

    @property
    def nickname(self):
        return self._nickname

    @nickname.setter
    def nickname(self, value):
        # TODO: Verification
        self._nickname = value

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, value):
        # TODO: Verification
        self._username = value

    @property
    def realname(self):
        return self._realname

    @realname.setter
    def realname(self, value):
        self._realname = value
