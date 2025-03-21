from typing import List

available_commands: List[str] = [
    'userinfo',
    'avatar'
]

from .general import General

__all__ = [
    'General',
    'available_commands'
]