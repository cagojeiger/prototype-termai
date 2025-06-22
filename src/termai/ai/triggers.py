"""
AI Trigger System for Terminal AI Assistant

This module provides trigger management for determining when AI analysis
should be activated based on terminal events and patterns.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from re import Pattern

from .context import CommandContext, CommandType


class TriggerType(Enum):
    """Types of AI triggers."""

    ERROR = "error"  # Command execution errors
    DANGEROUS = "dangerous"  # Potentially harmful commands
    PATTERN = "pattern"  # Specific output patterns
    MANUAL = "manual"  # User-requested analysis
    PERIODIC = "periodic"  # Time-based triggers
    CONTEXT = "context"  # Context-based triggers


@dataclass
class Trigger:
    """Dataclass defining AI activation rules with patterns and priorities."""

    name: str
    trigger_type: TriggerType
    priority: int  # 1-10, higher = more important
    pattern: str | None = None  # Regex pattern for matching
    description: str = ""
    enabled: bool = True
    cooldown_seconds: int = 0  # Minimum time between triggers
    last_triggered: float = 0.0

    def __post_init__(self):
        """Compile regex pattern if provided."""
        self._compiled_pattern: Pattern | None = None
        if self.pattern:
            try:
                self._compiled_pattern = re.compile(
                    self.pattern, re.IGNORECASE | re.MULTILINE
                )
            except re.error as e:
                raise ValueError(f"Invalid regex pattern '{self.pattern}': {e}") from e

    def matches(self, text: str) -> bool:
        """Check if trigger pattern matches the given text."""
        if not self.enabled:
            return False

        if not self._compiled_pattern:
            return False

        return bool(self._compiled_pattern.search(text))

    def can_trigger(self) -> bool:
        """Check if trigger can fire (respects cooldown)."""
        if not self.enabled:
            return False

        if self.cooldown_seconds <= 0:
            return True

        return (time.time() - self.last_triggered) >= self.cooldown_seconds

    def trigger(self):
        """Mark trigger as fired."""
        self.last_triggered = time.time()


class TriggerManager:
    """Evaluates terminal events to determine when AI analysis should activate."""

    def __init__(self):
        self.triggers: list[Trigger] = []
        self.trigger_history: list[dict] = []
        self.max_history = 100

        self.callbacks: dict[TriggerType, list[Callable]] = {
            trigger_type: [] for trigger_type in TriggerType
        }

        self._init_default_triggers()

    def _init_default_triggers(self):
        """Initialize default trigger patterns."""

        self.add_trigger(
            Trigger(
                name="command_error",
                trigger_type=TriggerType.ERROR,
                priority=10,
                description="Any command that exits with non-zero code",
                cooldown_seconds=1,
            )
        )

        dangerous_patterns = [
            (r"rm\s+-rf\s+/", "Recursive delete from root"),
            (r"sudo\s+rm\s+-rf", "Sudo recursive delete"),
            (r"mkfs\.", "Format filesystem"),
            (r"dd\s+if=.*of=/dev/", "Direct disk write"),
            (r">\s*/dev/sd[a-z]", "Write to disk device"),
            (r"chmod\s+777\s+/", "Dangerous permissions on root"),
        ]

        for pattern, desc in dangerous_patterns:
            self.add_trigger(
                Trigger(
                    name=f"dangerous_{desc.lower().replace(' ', '_')}",
                    trigger_type=TriggerType.DANGEROUS,
                    priority=9,
                    pattern=pattern,
                    description=desc,
                    cooldown_seconds=5,
                )
            )

        error_patterns = [
            (r"permission denied", "Permission denied errors"),
            (r"no such file or directory", "File not found errors"),
            (r"command not found", "Command not found errors"),
            (r"connection refused", "Network connection errors"),
            (r"out of space", "Disk space errors"),
            (r"cannot allocate memory", "Memory allocation errors"),
            (r"segmentation fault", "Segmentation fault errors"),
            (r"killed", "Process killed"),
        ]

        for pattern, desc in error_patterns:
            self.add_trigger(
                Trigger(
                    name=f"error_pattern_{desc.lower().replace(' ', '_')}",
                    trigger_type=TriggerType.PATTERN,
                    priority=8,
                    pattern=pattern,
                    description=desc,
                    cooldown_seconds=2,
                )
            )

        git_patterns = [
            (r"merge conflict", "Git merge conflicts"),
            (r"fatal: not a git repository", "Not in git repository"),
            (r"nothing to commit", "Git status - clean"),
            (r"untracked files", "Git untracked files"),
            (r"changes not staged", "Git unstaged changes"),
        ]

        for pattern, desc in git_patterns:
            self.add_trigger(
                Trigger(
                    name=f"git_{desc.lower().replace(' ', '_')}",
                    trigger_type=TriggerType.PATTERN,
                    priority=6,
                    pattern=pattern,
                    description=desc,
                    cooldown_seconds=10,
                )
            )

        package_patterns = [
            (r"package not found", "Package not found"),
            (r"dependency.*not satisfied", "Dependency issues"),
            (r"npm ERR!", "NPM errors"),
            (r"pip.*error", "Pip errors"),
            (r"E: Unable to locate package", "APT package not found"),
        ]

        for pattern, desc in package_patterns:
            self.add_trigger(
                Trigger(
                    name=f"package_{desc.lower().replace(' ', '_')}",
                    trigger_type=TriggerType.PATTERN,
                    priority=7,
                    pattern=pattern,
                    description=desc,
                    cooldown_seconds=5,
                )
            )

        dev_patterns = [
            (r"compilation terminated", "Compilation errors"),
            (r"build failed", "Build failures"),
            (r"test.*failed", "Test failures"),
            (r"syntax error", "Syntax errors"),
            (r"import.*error", "Import errors"),
            (r"module not found", "Module not found"),
        ]

        for pattern, desc in dev_patterns:
            self.add_trigger(
                Trigger(
                    name=f"dev_{desc.lower().replace(' ', '_')}",
                    trigger_type=TriggerType.PATTERN,
                    priority=7,
                    pattern=pattern,
                    description=desc,
                    cooldown_seconds=3,
                )
            )

    def add_trigger(self, trigger: Trigger):
        """Add a new trigger to the manager."""
        self.triggers.append(trigger)
        self.triggers.sort(key=lambda t: t.priority, reverse=True)

    def remove_trigger(self, name: str) -> bool:
        """Remove a trigger by name."""
        for i, trigger in enumerate(self.triggers):
            if trigger.name == name:
                del self.triggers[i]
                return True
        return False

    def enable_trigger(self, name: str) -> bool:
        """Enable a trigger by name."""
        for trigger in self.triggers:
            if trigger.name == name:
                trigger.enabled = True
                return True
        return False

    def disable_trigger(self, name: str) -> bool:
        """Disable a trigger by name."""
        for trigger in self.triggers:
            if trigger.name == name:
                trigger.enabled = False
                return True
        return False

    def evaluate_command(self, context: CommandContext) -> list[Trigger]:
        """Evaluate a command context and return triggered triggers."""
        triggered = []

        if context.exit_code != 0:
            error_triggers = [
                t
                for t in self.triggers
                if t.trigger_type == TriggerType.ERROR and t.can_trigger()
            ]
            for trigger in error_triggers:
                trigger.trigger()
                triggered.append(trigger)
                self._log_trigger(trigger, context)

        if context.command_type == CommandType.DANGEROUS:
            dangerous_triggers = [
                t
                for t in self.triggers
                if t.trigger_type == TriggerType.DANGEROUS and t.can_trigger()
            ]
            for trigger in dangerous_triggers:
                if trigger.matches(context.command):
                    trigger.trigger()
                    triggered.append(trigger)
                    self._log_trigger(trigger, context)

        text_to_check = f"{context.command}\n{context.output}\n{context.error}"
        pattern_triggers = [
            t
            for t in self.triggers
            if t.trigger_type == TriggerType.PATTERN and t.can_trigger()
        ]

        for trigger in pattern_triggers:
            if trigger.matches(text_to_check):
                trigger.trigger()
                triggered.append(trigger)
                self._log_trigger(trigger, context)

        triggered.sort(key=lambda t: t.priority, reverse=True)
        return triggered

    def evaluate_manual_request(self, request: str) -> list[Trigger]:
        """Evaluate a manual AI request."""
        manual_trigger = Trigger(
            name="manual_request",
            trigger_type=TriggerType.MANUAL,
            priority=10,
            description=f"Manual request: {request[:50]}...",
        )

        manual_trigger.trigger()
        self._log_trigger(manual_trigger, None)
        return [manual_trigger]

    def should_analyze(self, context: CommandContext) -> bool:
        """Quick check if any analysis should be triggered."""
        triggered = self.evaluate_command(context)
        return len(triggered) > 0

    def get_trigger_by_name(self, name: str) -> Trigger | None:
        """Get a trigger by name."""
        for trigger in self.triggers:
            if trigger.name == name:
                return trigger
        return None

    def get_triggers_by_type(self, trigger_type: TriggerType) -> list[Trigger]:
        """Get all triggers of a specific type."""
        return [t for t in self.triggers if t.trigger_type == trigger_type]

    def register_callback(self, trigger_type: TriggerType, callback: Callable):
        """Register a callback for a trigger type."""
        self.callbacks[trigger_type].append(callback)

    def _log_trigger(self, trigger: Trigger, context: CommandContext | None):
        """Log trigger activation."""
        log_entry = {
            "timestamp": time.time(),
            "trigger_name": trigger.name,
            "trigger_type": trigger.trigger_type.value,
            "priority": trigger.priority,
            "command": context.command if context else None,
            "exit_code": context.exit_code if context else None,
        }

        self.trigger_history.append(log_entry)

        if len(self.trigger_history) > self.max_history:
            self.trigger_history.pop(0)

        for callback in self.callbacks[trigger.trigger_type]:
            try:
                callback(trigger, context)
            except Exception as e:
                print(f"Trigger callback error: {e}")

    def get_trigger_statistics(self) -> dict:
        """Get statistics about trigger activations."""
        if not self.trigger_history:
            return {"total_triggers": 0}

        total_triggers = len(self.trigger_history)

        type_counts: dict[str, int] = {}
        for entry in self.trigger_history:
            trigger_type = entry["trigger_type"]
            type_counts[trigger_type] = type_counts.get(trigger_type, 0) + 1

        recent_time = time.time() - 3600
        recent_triggers = [
            e for e in self.trigger_history if e["timestamp"] > recent_time
        ]

        return {
            "total_triggers": total_triggers,
            "type_distribution": type_counts,
            "recent_triggers": len(recent_triggers),
            "most_common_trigger": (
                max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
            ),
        }

    def clear_history(self):
        """Clear trigger history."""
        self.trigger_history.clear()
