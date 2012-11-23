# -*- coding: utf8 -*-
__all__ = ('CoreClient',)

import gevent
import gevent.ssl
import gevent.socket
import gevent.queue

from utopia.plugins import PluginList
from utopia.protocol import parse_message
from utopia.client.user import User


class CoreClient(object):
    """
    A minimal client which does nothing other than connect, handle basic IO,
    and dispatch messages.
    """
    def __init__(self, host, port=6667, use_ssl=False):
        self._in_queue = gevent.queue.Queue()
        self._out_queue = gevent.queue.Queue()
        self._socket = None
        self._chunk_size = 4096
        self._shutting_down = False
        self._jobs = None
        self._address = (host, port)
        self._use_ssl = use_ssl
        self._user = User(self)
        self._plugins = PluginList(self)

    def close(self):
        """
        Closes the client connection, attempting to do so gracefully.
        Automatically called when the `Client` is garbage collected.
        """
        self._plugin_event('event_closing', None, self)

    @property
    def address(self):
        return self._address

    @property
    def use_ssl(self):
        return self._use_ssl

    @property
    def socket(self):
        """
        The raw gevent socket in use by this `Client`.
        """
        return self._socket

    @property
    def plugins(self):
        """
        The currently loaded plugins on this Client.
        """
        return self._plugins

    @property
    def user(self):
        return self._user

    def __del__(self):
        """
        Make sure we're closed when we get collected.
        """
        self.close()

    def connect(self):
        """
        Connect to the remote server and begin working, returning
        immediately without blocking.
        """
        self._socket = gevent.socket.create_connection(self._address)
        if self._use_ssl:
            self._socket = gevent.ssl.wrap_socket(self._socket)

        self._jobs = (
            gevent.spawn(self._read_handler),
            gevent.spawn(self._write_handler)
        )

        self._plugin_event('event_connected', None, self)

    def _read_handler(self):
        """
        Handles reading complete lines from the server.
        """
        read_buffer = ''
        while not self._shutting_down:
            read_tmp = self.socket.recv(self._chunk_size)
            # Remote end disconnected.
            if not read_tmp:
                self.close()
                return
            # Process any complete lines.
            read_buffer += read_tmp
            while '\r\n' in read_buffer:
                line, read_buffer = read_buffer.split('\r\n', 1)
                message = parse_message(line)
                method = 'msg_{0}'.format(message.command.lower())
                self._plugin_event(method, 'msg_not_handled', self, message)

    def _plugin_event(self, method, default, *args, **kwargs):
        for plugin in self._plugins.plugins:
            f_method = getattr(plugin, method, None)
            if f_method is None and default is not None:
                f_method = getattr(plugin, default, None)
                if f_method is None:
                    continue
            f_method(*args, **kwargs)

    def _write_handler(self):
        """
        Handles writing complete lines to the server.
        """
        while not self._shutting_down:
            to_send = self._out_queue.get()
            while to_send:
                bytes_sent = self.socket.send(to_send)
                to_send = to_send[bytes_sent:]

    def send(self, command, args, c=False):
        """
        Adds a new message to the outgoing message queue. If `c` is `True`,
        the last arugment is prefixed with a colon.
        """
        if c and args:
            args[-1] = ':{0!s}'.format(args[-1])

        message = '{0} {1}\r\n'.format(command, ' '.join(args))
        self._out_queue.put(message.encode('utf8'))
