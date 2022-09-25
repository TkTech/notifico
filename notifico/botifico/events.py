import enum


class Event(enum.Enum):
    on_connected = 'on_connected'
    on_disconnect = 'on_disconnect'
    on_message = 'on_message'

    #: End of /motd command.
    RPL_ENDOFMOTD = '376'

    #: Server's MOTD fild could not be opened.
    ERR_NOMOTD = '422'
