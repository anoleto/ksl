from typing import List

available_commands: List[str] = [
    'ping',
    'info',
    'eval'
]

from .ping import Ping
from .info import Info
from .owner import Owner

__all__ = [
    'Ping',
    'Info',
    'Owner',
    'available_commands'
]