# -*- coding: utf8 -*-
__all__ = ('parse_prefix', 'parse_message', 'Responses', 'Errors')

import re
from collections import namedtuple

PREFIX_R = re.compile(r'([^!]*)!?([^@]*)@?(.*)')

parsed_line = namedtuple('parsed_line', [
    'prefix',
    'command',
    'args'
])

parsed_prefix = namedtuple('parsed_prefix', [
    'nickname',
    'username',
    'hostname'
])


def parse_prefix(prefix):
    """
    Parses a message prefix, returning the nickname, username, and host
    as a tuple.
    """
    return PREFIX_R.match(prefix).groups()


def parse_message(line):
    """
    Parses IRC messages from the server.
    """
    # Ganked from Twisted.
    prefix = ''
    trailing = []
    if not line:
        raise ValueError('Empty line.')
    if line[0] == ':':
        prefix, line = line[1:].split(' ', 1)
    if line.find(' :') != -1:
        line, trailing = line.split(' :', 1)
        args = line.split()
        args.append(trailing)
    else:
        args = line.split()
    command = args.pop(0)
    return parsed_line(prefix, command, args)


class Errors(object):
    """
    RFC 1459 Error Responses.
    """
    NOSUCHNICK = '401'
    NOSUCHSERVER = '402'
    NOSUCHCHANNEL = '403'
    CANNOTSENDTOCHAN = '404'
    TOOMANYCHANNELS = '405'
    WASNOSUCHNICK = '406'
    TOOMANYTARGETS = '407'
    NOORIGIN = '409'
    NORECIPIENT = '411'
    NOTEXTTOSEND = '412'
    NOTOPLEVEL = '413'
    WILDTOPLEVEL = '414'
    UNKNOWNCOMMAND = '421'
    NOMOTD = '422'
    NOADMININFO = '423'
    FILEERROR = '424'
    NONICKNAMEGIVEN = '431'
    ERRONEUSNICKNAME = '432'
    NICKNAMEINUSE = '433'
    NICKCOLLISION = '436'
    USERNOTINCHANNEL = '441'
    NOTONCHANNEL = '442'
    USERONCHANNEL = '443'
    NOLOGIN = '444'
    SUMMONDISABLED = '445'
    USERSDISABLED = '446'
    NOTREGISTERED = '451'
    NEEDMOREPARAMS = '461'
    ALREADYREGISTRED = '462'
    NOPERMFORHOST = '463'
    PASSWDMISMATCH = '464'
    YOUREBANNEDCREEP = '465'
    KEYSET = '467'
    CHANNELISFULL = '471'
    UNKNOWNMODE = '472'
    INVITEONLYCHAN = '473'
    BANNEDFROMCHAN = '474'
    BADCHANNELKEY = '475'
    NOPRIVILEGES = '481'
    CHANOPRIVSNEEDED = '482'
    CANTKILLSERVER = '483'
    NOOPERHOST = '491'
    UMODEUNKNOWNFLAG = '501'
    USERSDONTMATCH = '502'


class Responses(object):
    """
    RFC 1459 Command Responses.
    """
    NONE = '300'
    USERHOST = '302'
    ISON = '303'
    AWAY = '301'
    UNAWAY = '305'
    NOWAWAY = '306'
    WHOISUSER = '311'
    WHOISSERVER = '312'
    WHOISOPERATOR = '313'
    WHOISIDLE = '317'
    ENDOFWHOIS = '318'
    WHOISCHANNELS = '319'
    WHOWASUSER = '314'
    ENDOFWHOWAS = '369'
    LISTSTART = '321'
    LIST = '322'
    LISTEND = '323'
    CHANNELMODEIS = '324'
    NOTOPIC = '331'
    TOPIC = '332'
    INVITING = '341'
    SUMMONING = '342'
    VERSION = '351'
    WHOREPLY = '352'
    ENDOFWHO = '315'
    NAMEREPLY = '353'
    ENDOFNAMES = '366'
    LINKS = '364'
    ENDOFLINKS = '365'
    BANLIST = '367'
    ENDOFBANLIST = '368'
    INFO = '371'
    ENDOFINFO = '374'
    MOTDSTART = '375'
    MOTD = '372'
    ENDOFMOTD = '376'
    YOUREOPER = '381'
    REHASHING = '382'
    TIME = '391'
    USERSSTART = '392'
    USERS = '393'
    ENDOFUSERS = '394'
    NOUSERS = '395'
    TRACELINK = '200'
    TRACECONNECTING = '201'
    TRACEHANDSHAKE = '202'
    TRACEUNKNOWN = '203'
    TRACEOPERATOR = '204'
    TRACEUSER = '205'
    TRACESERVER = '206'
    TRACENEWTYPE = '208'
    TRACELOG = '261'
    STATSLINKINFO = '211'
    STATSCOMMANDS = '212'
    STATSCLINE = '213'
    STATSNLINE = '214'
    STATSILINE = '215'
    STATSKLINE = '216'
    STATSYLINE = '218'
    ENDOFSTATS = '219'
    STATSLLINE = '241'
    STATSUPTIME = '242'
    STATSOLINE = '243'
    STATSHLINE = '244'
    UMODEIS = '221'
    LUSERCLIENT = '251'
    LUSEROP = '252'
    LUSERUNKNOWN = '253'
    LUSERCHANNELS = '254'
    LUSERME = '255'
    ADMINME = '256'
    ADMINLOC1 = '257'
    ADMINLOC2 = '258'
    ADMINEMAIL = '259'
