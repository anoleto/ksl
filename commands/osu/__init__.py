from typing import List

available_commands: List[str] = [
    'profile'
    'setprofile'
    'recent'
    'top'
    'changemod'
]

from .tools import Tools
from .profile import Profile
from .score import Score

__all__ = [
    'Profile',
    'Score',
    'Tools',
    'available_commands'
]

# XXX: maybe later?
# XXX: gotta rewrite my whole recent, top, etc command again :sob: