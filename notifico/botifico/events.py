import enum


class Event(enum.Enum):
    #: Triggered when a Bot connects.
    on_connected = 'on_connected'
    #: Triggered when a Bot disconnects.
    on_disconnect = 'on_disconnect'
    #: Triggered when a message is received.
    on_message = 'on_message'

    #: Called just before a message is written to a Bot' socket, useful for
    #: implementing rate limiting.
    on_write = 'on_write'

    #: End of /motd command.
    RPL_ENDOFMOTD = '376'

    #: Server's MOTD fild could not be opened.
    ERR_NOMOTD = '422'
