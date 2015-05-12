from collections import namedtuple


Channel = namedtuple('Channel', ['channel', 'password'])
_network = namedtuple('Network', ['host', 'port', 'ssl', 'password'])


class Network(_network):
    __slots__ = ()

    @classmethod
    def new(cls, host, port=6667, ssl=False, password=None):
        return cls(
            host=host,
            port=port,
            ssl=ssl,
            password=password
        )

    @classmethod
    def from_client(cls, client):
        return cls(
            host=client.host,
            port=client.port,
            ssl=client.ssl,
            password=client.identity.password
        )
