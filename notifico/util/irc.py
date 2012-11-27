# -*- coding: utf8 -*-
"""
Generic IRC utilities.
"""
__all__ = ('mirc_colors', 'strip_mirc_colors')
import re

#: Precompiled regex for matching mIRC color codes.
_STRIP_R = re.compile('\x03(?:\d{1,2}(?:,\d{1,2})?)?', re.UNICODE)

#: Common mIRC color codes.
_colors = dict(
    RESET='\x03',
    WHITE='\x03' + '00',
    BLACK='\x03' + '01',
    BLUE='\x03' + '02',
    GREEN='\x03' + '03',
    RED='\x03' + '04',
    BROWN='\x03' + '05',
    PURPLE='\x03' + '06',
    ORANGE='\x03' + '07',
    YELLOW='\x03' + '08',
    LIGHT_GREEN='\x03' + '09',
    TEAL='\x03' + '10',
    LIGHT_CYAN='\x03' + '11',
    LIGHT_BLUE='\x03' + '12',
    PINK='\x03' + '13'
)


def mirc_colors():
    """
    Returns a dictionary mapping color names to common mIRC color
    codes.
    """
    return _colors


def strip_mirc_colors(msg):
    """
    Strips mIRC color codes from `msg`, returning the new string.
    """
    return _STRIP_R.sub('', msg)
