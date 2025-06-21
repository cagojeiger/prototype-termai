"""
Context Management for Terminal AI Assistant

This module provides context window management and data structures
for maintaining relevant terminal session information for AI analysis.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from collections import deque
from typing import Deque
from enum import Enum


class CommandType(Enum):
    """Classification of command types for relevance scoring."""
    
    NAVIGATION = "navigation"  # cd, ls, pwd
    FILE_OPERATION = "file_op"  # cp, mv, rm, mkdir
    TEXT_PROCESSING = "text"  # grep, sed, awk, cat
    SYSTEM_INFO = "system"  # ps, top, df, free
    NETWORK = "network"  # curl, wget, ping, ssh
    VERSION_CONTROL = "git"  # git commands
    PACKAGE_MANAGEMENT = "package"  # npm, pip, apt, brew
    DEVELOPMENT = "dev"  # make, cargo, python, node
    DANGEROUS = "dangerous"  # rm -rf, sudo rm, format
    OTHER = "other"


@dataclass
class CommandContext:
    """Context information for a single command execution."""
    
    command: str
    directory: str
    timestamp: float
    exit_code: int
    output: str
    error: str
    duration: float
    command_type: CommandType
    relevance_score: float = 0.0
    
    def __post_init__(self) -> None:
        """Calculate relevance score after initialization."""
        self.relevance_score = self._calculate_relevance()
    
    def _calculate_relevance(self) -> float:
        """Calculate relevance score based on command characteristics."""
        base_score = 0.5
        
        if self.exit_code != 0:
            base_score = 0.9
        
        type_scores = {
            CommandType.DANGEROUS: 0.95,
            CommandType.VERSION_CONTROL: 0.8,
            CommandType.DEVELOPMENT: 0.8,
            CommandType.PACKAGE_MANAGEMENT: 0.7,
            CommandType.FILE_OPERATION: 0.6,
            CommandType.NETWORK: 0.6,
            CommandType.TEXT_PROCESSING: 0.5,
            CommandType.SYSTEM_INFO: 0.4,
            CommandType.NAVIGATION: 0.3,
            CommandType.OTHER: 0.4
        }
        
        type_score = type_scores.get(self.command_type, 0.4)
        base_score = max(base_score, type_score)
        
        age_minutes = (time.time() - self.timestamp) / 60
        if age_minutes < 5:
            base_score += 0.1 * (5 - age_minutes) / 5
        
        if len(self.output) > 1000:
            base_score += 0.05
        elif len(self.output) > 100:
            base_score += 0.02
        
        return min(0.99, base_score)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "command": self.command,
            "directory": self.directory,
            "timestamp": self.timestamp,
            "exit_code": self.exit_code,
            "output": self.output[:500],  # Truncate for storage
            "error": self.error[:200],
            "duration": self.duration,
            "command_type": self.command_type.value,
            "relevance_score": self.relevance_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CommandContext':
        """Create from dictionary."""
        return cls(
            command=data["command"],
            directory=data["directory"],
            timestamp=data["timestamp"],
            exit_code=data["exit_code"],
            output=data["output"],
            error=data["error"],
            duration=data["duration"],
            command_type=CommandType(data["command_type"]),
            relevance_score=data["relevance_score"]
        )


@dataclass
class SessionContext:
    """Session-wide context information."""
    
    current_directory: str
    shell_type: str
    environment_vars: Dict[str, str] = field(default_factory=dict)
    active_processes: List[str] = field(default_factory=list)
    git_status: Optional[Dict] = None
    system_info: Dict[str, str] = field(default_factory=dict)
    
    def update_git_status(self, branch: str, status: str, has_changes: bool) -> None:
        """Update git repository status."""
        self.git_status = {
            "branch": branch,
            "status": status,
            "has_changes": has_changes,
            "updated_at": time.time()
        }
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "current_directory": self.current_directory,
            "shell_type": self.shell_type,
            "environment_vars": dict(self.environment_vars),
            "active_processes": list(self.active_processes),
            "git_status": self.git_status,
            "system_info": dict(self.system_info)
        }


class ContextWindow:
    """Manages sliding window of CommandContext objects with token limits."""
    
    def __init__(self, max_commands: int = 20, max_tokens: int = 4000):
        self.max_commands = max_commands
        self.max_tokens = max_tokens
        self.commands: Deque[CommandContext] = deque(maxlen=max_commands)
        self.session: SessionContext = SessionContext(
            current_directory="/",
            shell_type="bash"
        )
        self._important_commands: List[CommandContext] = []
    
    def add_command(self, context: CommandContext) -> None:
        """Add a new command context to the window."""
        self.commands.append(context)
        
        if context.relevance_score >= 0.8:
            self._important_commands.append(context)
            if len(self._important_commands) > 10:
                self._important_commands.pop(0)
    
    def get_relevant_context(self, max_tokens: Optional[int] = None) -> List[CommandContext]:
        """Get most relevant commands within token limit."""
        max_tokens = max_tokens or self.max_tokens
        
        all_commands = list(self.commands) + self._important_commands
        
        seen = set()
        unique_commands = []
        for cmd in reversed(all_commands):  # Start with most recent
            cmd_key = (cmd.command, cmd.timestamp)
            if cmd_key not in seen:
                seen.add(cmd_key)
                unique_commands.append(cmd)
        
        unique_commands.sort(key=lambda x: x.relevance_score, reverse=True)
        
        selected = []
        current_tokens = 0
        
        for cmd in unique_commands:
            cmd_tokens = (len(cmd.command) + len(cmd.output) + len(cmd.error)) // 4
            
            if current_tokens + cmd_tokens <= max_tokens:
                selected.append(cmd)
                current_tokens += cmd_tokens
            else:
                break
        
        selected.sort(key=lambda x: x.timestamp)
        return selected
    
    def get_error_commands(self, limit: int = 5) -> List[CommandContext]:
        """Get recent commands that resulted in errors."""
        error_commands = [cmd for cmd in self.commands if cmd.exit_code != 0]
        return sorted(error_commands, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def get_commands_by_type(self, command_type: CommandType, limit: int = 10) -> List[CommandContext]:
        """Get recent commands of specific type."""
        type_commands = [cmd for cmd in self.commands if cmd.command_type == command_type]
        return sorted(type_commands, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def update_session_context(self, **kwargs) -> None:
        """Update session context information."""
        for key, value in kwargs.items():
            if hasattr(self.session, key):
                setattr(self.session, key, value)
    
    def get_context_summary(self) -> str:
        """Get a text summary of current context for AI prompts."""
        recent_commands = list(self.commands)[-5:]  # Last 5 commands
        error_commands = self.get_error_commands(3)
        
        summary_parts = [
            f"Current Directory: {self.session.current_directory}",
            f"Shell: {self.session.shell_type}"
        ]
        
        if self.session.git_status:
            git = self.session.git_status
            summary_parts.append(f"Git: {git['branch']} ({'clean' if not git['has_changes'] else 'modified'})")
        
        if recent_commands:
            summary_parts.append("Recent Commands:")
            for cmd in recent_commands:
                status = "✓" if cmd.exit_code == 0 else "✗"
                summary_parts.append(f"  {status} {cmd.command}")
        
        if error_commands:
            summary_parts.append("Recent Errors:")
            for cmd in error_commands:
                summary_parts.append(f"  ✗ {cmd.command} (exit {cmd.exit_code})")
        
        return "\n".join(summary_parts)
    
    def clear(self) -> None:
        """Clear all context data."""
        self.commands.clear()
        self._important_commands.clear()
    
    def get_statistics(self) -> Dict:
        """Get context window statistics."""
        if not self.commands:
            return {"total_commands": 0}
        
        total_commands = len(self.commands)
        error_count = sum(1 for cmd in self.commands if cmd.exit_code != 0)
        
        type_counts: Dict[str, int] = {}
        for cmd in self.commands:
            type_name = cmd.command_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        avg_relevance = sum(cmd.relevance_score for cmd in self.commands) / total_commands
        
        return {
            "total_commands": total_commands,
            "error_count": error_count,
            "error_rate": error_count / total_commands,
            "command_types": type_counts,
            "average_relevance": avg_relevance,
            "important_commands": len(self._important_commands)
        }


def classify_command(command: str) -> CommandType:
    """Classify command type based on the command string."""
    command = command.strip().lower()
    
    if any(pattern in command for pattern in [
        'rm -rf', 'sudo rm', 'format', 'mkfs', 'dd if=', '> /dev/'
    ]):
        return CommandType.DANGEROUS
    
    if command.startswith('git '):
        return CommandType.VERSION_CONTROL
    
    if any(command.startswith(pm) for pm in [
        'npm ', 'yarn ', 'pip ', 'pip3 ', 'apt ', 'brew ', 'yum ', 'dnf ', 'pacman '
    ]):
        return CommandType.PACKAGE_MANAGEMENT
    
    if any(command.startswith(dev) for dev in [
        'make ', 'cargo ', 'python ', 'python3 ', 'node ', 'npm run', 'yarn run'
    ]):
        return CommandType.DEVELOPMENT
    
    if any(command.startswith(net) for net in [
        'curl ', 'wget ', 'ping ', 'ssh ', 'scp ', 'rsync '
    ]):
        return CommandType.NETWORK
    
    if any(command.startswith(file_op) for file_op in [
        'cp ', 'mv ', 'rm ', 'mkdir ', 'rmdir ', 'chmod ', 'chown ', 'ln '
    ]):
        return CommandType.FILE_OPERATION
    
    if any(command.startswith(text) for text in [
        'grep ', 'sed ', 'awk ', 'cat ', 'less ', 'more ', 'head ', 'tail ', 'sort ', 'uniq '
    ]):
        return CommandType.TEXT_PROCESSING
    
    if any(command.startswith(sys) for sys in [
        'ps ', 'top ', 'htop ', 'df ', 'du ', 'free ', 'uptime ', 'who ', 'w '
    ]):
        return CommandType.SYSTEM_INFO
    
    if any(command.startswith(nav) for nav in ['cd ', 'ls ', 'pwd', 'find ']):
        return CommandType.NAVIGATION
    
    return CommandType.OTHER
