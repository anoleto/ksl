# XXX: this logging was made by cmyui,
# https://github.com/cmyui/cmyui_pkg/blob/master/cmyui/logging.py
# NOTE: used this because for clean logging
import sys
import colorsys

from datetime import tzinfo
from datetime import datetime
from datetime import timezone

from enum import IntEnum
from functools import cache
from functools import lru_cache

from typing import Union
from typing import Optional
from typing import overload

from zoneinfo import ZoneInfo

__all__ = ('Ansi', 'RGB', 'Rainbow', 'printc',
           '_fmt_rainbow', 'print_rainbow',
           'set_timezone', 'log')

class Ansi(IntEnum):
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37

    GRAY     = 90
    LRED     = 91
    LGREEN   = 92
    LYELLOW  = 93
    LBLUE    = 94
    LMAGENTA = 95
    LCYAN    = 96
    LWHITE   = 97

    RESET = 0

    @cache
    def __repr__(self) -> str:
        return f'\x1b[{self.value}m'

class RGB:
    @overload
    def __init__(self, rgb: int) -> None: ...
    @overload
    def __init__(self, r: int, g: int, b: int) -> None: ...

    def __init__(self, *args) -> None:
        largs = len(args)

        if largs == 3:
            self.r, self.g, self.b = args
        elif largs == 1:
            rgb = args[0]
            self.b = rgb & 0xff
            self.g = (rgb >> 8) & 0xff
            self.r = (rgb >> 16) & 0xff
        else:
            raise ValueError('Incorrect params for RGB.')

    @lru_cache(maxsize=64)
    def __repr__(self) -> str:
        return f'\x1b[38;2;{self.r};{self.g};{self.b}m'

class _Rainbow: ...

Rainbow = _Rainbow()

Colour_Types = Union[Ansi, RGB, _Rainbow]

stdout_write = sys.stdout.write
stdout_flush = sys.stdout.flush

_gray = repr(Ansi.GRAY)
_reset = repr(Ansi.RESET)

def printc(msg: str, col: Colour_Types, end: str = '\n') -> None:
    """Print a string, in a specified ansi colour."""
    stdout_write(f'{col!r}{msg}{_reset}{end}')
    stdout_flush()

def _fmt_rainbow(msg: str, end: float = 2 / 3) -> None:
    cols = [RGB(*map(int, rgb)) for rgb in rainbow_color_stops(n=len(msg), end=end)]
    return ''.join([f'{cols[i]!r}{c}' for i, c in enumerate(msg)]) + repr(Ansi.RESET)

def print_rainbow(msg: str, rainbow_end: float = 2 / 3, end: str = '\n') -> None:
    stdout_write(f'{_fmt_rainbow(msg, rainbow_end)}{end}')
    stdout_flush()

# TODO: better solution than this; this at least requires the
# iana/tzinfo database to be installed, meaning it's limited.
#_log_tz = ZoneInfo('GMT') # default
_log_tz = timezone.utc

def set_timezone(tz: tzinfo) -> None:
    global _log_tz
    _log_tz = tz

def log(msg: str, col: Optional[Colour_Types] = None,
        file: Optional[str] = None, end: str = '\n') -> None:
    """\
    Print a string, in a specified ansi colour with timestamp.

    Allows for the functionality to write to a file as
    well by passing the filepath with the `file` parameter.
    """

    ts_short = get_timestamp(full=False, tz=_log_tz)

    if col:
        if col is Rainbow:
            print_rainbow(msg, end=end)
        else:
            stdout_write(f'{_gray}[{ts_short}] {col!r}{msg}{_reset}{end}')
    else:
        stdout_write(f'{_gray}[{ts_short}]{_reset} {msg}{end}')

    stdout_flush()

    if file:
        with open(file, 'a+') as f:
            f.write(f'[{get_timestamp(full=True, tz=_log_tz)}] {msg}\n')

def get_timestamp(
    full: bool = False,
    tz: Optional[tzinfo] = None
) -> str:
    fmt = '%d/%m/%Y %I:%M:%S%p' if full else '%I:%M:%S%p'
    return f'{datetime.now(tz=tz):{fmt}}'

def rainbow_color_stops(
    n: int = 10,
    lum: float = 0.5,
    end: float = 2 / 3
) -> list[tuple[int, int, int]]:
    # https://stackoverflow.com/a/58811633
    return [
        (r * 255, g * 255, b * 255)
        for r, g, b in [colorsys.hls_to_rgb(end * i / (n - 1), lum, 1)
                        for i in range(n)]
    ]
