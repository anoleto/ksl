from typing import List

available_commands: List[str] = [
    'wordbomb',
    'nowplaying',
    'setlastfm'
]

from .wordbomb import WordBomb
from .lastfm import LastFM
__all__ = [
    'WordBomb',
    'LastFM',
    'available_commands'
]