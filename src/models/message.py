from dataclasses import dataclass
from typing import Literal

@dataclass
class Message:
    """Represents a chat message"""
    role: Literal["user", "assistant", "system"]
    content: str