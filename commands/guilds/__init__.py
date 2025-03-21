from typing import List

available_commands: List[str] = [
    'setprefix',
    'prefix',
    'resetprefix'
]

from .prefix import Prefix

__all__ = [
    'Prefix',
    'available_commands'
]