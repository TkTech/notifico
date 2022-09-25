import dataclasses
from typing import Optional


@dataclasses.dataclass
class Prefix:
    nick: str
    user: Optional[str] = None
    host: Optional[str] = None


def unpack_prefix(prefix):
    """
    Unpacks an IRC message prefix.
    """
    host = None
    user = None

    if '@' in prefix:
        prefix, host = prefix.split('@', 1)

    if '!' in prefix:
        prefix, user = prefix.split('!', 1)

    return Prefix(nick=prefix, user=user, host=host)


def unpack_message(line):
    """
    Unpacks a complete, RFC compliant IRC message, returning the
    [optional] prefix, command, and parameters.

    :param line: An RFC compliant IRC message.
    """
    if not line:
        return None

    prefix = None

    line = line.rstrip()

    if line[0] == ':':
        prefix, line = line[1:].split(' ', 1)
        prefix = unpack_prefix(prefix)
    if ' :' in line:
        line, trailing = line.split(' :', 1)
        args = line.split()
        args.append(trailing)
    else:
        args = line.split()

    try:
        command = args.pop(0)
    except IndexError:
        command = ''

    return prefix, command.upper(), args
