"""
Generate a color based on an object's hash value.

Quick start:

>>> c = ColorHash('Hello World')
>>> c.hsl
(131, 0.65, 0.5)
>>> c.rgb
(45, 210, 75)
>>> c.hex
'#2dd24b'

Copyright (c) 2016 Felix Krull f_krull@gmx.de

This is a port of the 'color-hash' Javascript library which is:

Copyright (c) 2015 Zeno Zeng

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from binascii import crc32
from numbers import Number
from typing import Any
from typing import Tuple
from typing import Union

IntOrFloat = Union[int, float]


def crc32_hash(obj: Any) -> int:
    """
    Generate a hash for ``obj``.

    This function first converts the object to a string and encodes it into
    UTF-8, then calculates and returns the CRC-32 checksum of the result. The
    hash is guaranteed to be as stable as the result of the object's ``__str__``
    method.
    """
    bs = str(obj).encode("utf-8")
    return crc32(bs) & 0xFFFFFFFF


def hsl2rgb(hsl: Tuple[IntOrFloat, float, float]) -> Tuple[int, int, int]:
    """
    Convert an HSL color value into RGB.

    >>> hsl2rgb((0, 1, 0.5))
    (255, 0, 0)
    """
    try:
        h, s, l = hsl  # noqa, I tolerate "l"
        h /= 360
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
    except TypeError:
        raise ValueError(hsl)

    rgb: list[int] = []
    for c in (h + 1 / 3, h, h - 1 / 3):
        if c < 0:
            c += 1
        elif c > 1:
            c -= 1

        if c < 1 / 6:
            c = p + (q - p) * 6 * c
        elif c < 0.5:
            c = q
        elif c < 2 / 3:
            c = p + (q - p) * 6 * (2 / 3 - c)
        else:
            c = p
        rgb.append(round(c * 255))

    return tuple(rgb)  # noqa


def rgb2hex(rgb: Tuple[int, int, int]) -> str:
    """
    Format an RGB color value into a hexadecimal color string.

    >>> rgb2hex((255, 0, 0))
    '#ff0000'
    """
    try:
        return "#%02x%02x%02x" % rgb
    except TypeError:
        raise ValueError(rgb)


def color_hash(
    obj: Any,
    hashfunc=crc32_hash,
    lightness=(0.35, 0.5, 0.65),
    saturation=(0.35, 0.5, 0.65),
    min_h=None,
    max_h=None,
) -> Tuple[int, float, float]:
    """
    Calculate the color for the given object.

    Args:
        obj: the value.
        hashfunc: the hash function to use. Must be a unary function returning
                  an integer. Defaults to ``crc32_hash``.
        lightness: a range of values, one of which will be picked for the
                   lightness component of the result. Can also be a single
                   number.
        saturation: a range of values, one of which will be picked for the
                    saturation component of the result. Can also be a single
                    number.
        min_h: if set, limit the hue component to this lower value.
        max_h: if set, limit the hue component to this upper value.

    Returns:
        A ``(H, S, L)`` tuple.
    """
    if isinstance(lightness, Number):
        lightness = [lightness]
    if isinstance(saturation, Number):
        saturation = [saturation]

    if min_h is None and max_h is not None:
        min_h = 0
    if min_h is not None and max_h is None:
        max_h = 360

    hash = hashfunc(obj)
    h = hash % 359
    if min_h is not None and max_h is not None:
        h = (h / 1000) * (max_h - min_h) + min_h
    hash //= 360
    s = saturation[hash % len(saturation)]
    hash //= len(saturation)
    l = lightness[hash % len(lightness)]  # noqa, I tolerate "l"

    return (h, s, l)


class ColorHash:
    """
    Generate a color value and provide it in several format.

    This class takes the same arguments as the ``color_hash`` function.

    Attributes:
        hsl: HSL representation of the color value.
        rgb: RGB representation of the color value.
        hex: hex-formatted RGB color value.
    """

    def __init__(self, *args, **kwargs):
        self.hsl: Tuple[int, float, float] = color_hash(*args, **kwargs)

    @property
    def rgb(self) -> Tuple[int, int, int]:
        return hsl2rgb(self.hsl)

    @property
    def hex(self) -> str:
        return rgb2hex(self.rgb)
