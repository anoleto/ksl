from typing import List

available_commands: List[str] = [
    'ping',
    'info',
    'eval'
]

from .ping import Ping
from .info import Info
from .eval import Eval

__all__ = [
    'Ping',
    'Info',
    'Eval',
    'available_commands'
]