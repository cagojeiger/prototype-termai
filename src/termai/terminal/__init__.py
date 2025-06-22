"""Terminal emulation module for prototype-termai

This module provides PTY-based terminal emulation with command history,
output buffering, and integrated management capabilities.
"""

from .buffer import OutputBuffer
from .emulator import TerminalEmulator
from .history import Command, CommandHistory
from .manager import TerminalManager

__all__ = [
    "TerminalEmulator",
    "OutputBuffer",
    "Command",
    "CommandHistory",
    "TerminalManager",
]
