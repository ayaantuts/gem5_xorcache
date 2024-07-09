from .simple import SingleChannelSimpleMemory
from .abstract_memory_system import AbstractMemorySystem

from typing import Optional


def SingleChannelSimple(
    size: Optional[str] = None,
) -> AbstractMemorySystem:
    return SingleChannelSimpleMemory("50ns", "0ns", "19.2GB/s", size=size)
