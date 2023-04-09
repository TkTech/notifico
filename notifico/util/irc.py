"""
Generic IRC utilities.
"""
__all__ = ('mirc_colors', 'strip_mirc_colors', 'to_html')
import re

from markupsafe import Markup, escape

#: Precompiled regex for matching mIRC color codes.
_STRIP_R = re.compile(r'\x03(?:\d{1,2}(?:,\d{1,2})?)?', re.UNICODE)

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


def to_html(message):
    c_to_c = {
        0: 'white',
        1: '#DADADA',
        2: '#7FA5EB',
        3: 'green',
        4: '#DB5858',
        5: 'brown',
        6: 'purple',
        7: 'orange',
        8: 'yellow',
        9: 'lightgreen',
        10: 'teal',
        11: '#25B8C2',
        12: 'lightblue',
        13: '#E36FB8'
    }

    def _mirc_to_span(m):
        return Markup(
            '<span style="color: {fore};">{text}</span>'.format(
                text=escape(m.group(3)),
                fore=c_to_c.get(int(m.group(1)), 'black"')
            )
        )

    m = []
    for line in message.split('\n'):
        m.append(
            re.sub(
                #r'\x03(\d{1,2}),?(\d{1,2})(.*?)\x03',
                #r'\x03([0-9]{1,2}),?([0-9]{1,2})(.*?)\x03',
                r'\x03(\d{1,2})(,[0-9]{1,2})?(.*?)\x03',
                _mirc_to_span,
                line,
            )
        )

    return Markup('<br/>'.join(m))
