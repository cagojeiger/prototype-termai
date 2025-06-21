"""
Context Filters for Terminal AI Assistant

This module provides data sanitization and filtering capabilities
to remove sensitive information and noise from terminal context.
"""

import re
from dataclasses import replace
from typing import Any, Dict, List, Tuple

from .context import CommandContext


class ContextFilter:
    """Sanitizes terminal data by masking sensitive info and removing noise."""

    def __init__(self):
        self.sensitive_patterns = [
            (r"[A-Za-z0-9]{20,}", "[API_KEY]"),
            (r"sk-[A-Za-z0-9]{48}", "[OPENAI_KEY]"),
            (r"ghp_[A-Za-z0-9]{36}", "[GITHUB_TOKEN]"),
            (r"gho_[A-Za-z0-9]{36}", "[GITHUB_OAUTH]"),
            (r"ghu_[A-Za-z0-9]{36}", "[GITHUB_USER_TOKEN]"),
            (r"ghs_[A-Za-z0-9]{36}", "[GITHUB_SERVER_TOKEN]"),
            (r"AKIA[0-9A-Z]{16}", "[AWS_ACCESS_KEY]"),
            (r"[A-Za-z0-9/+=]{40}", "[AWS_SECRET_KEY]"),
            (
                r"postgresql://[^:]+:[^@]+@[^/]+/[^\s]+",
                "postgresql://[USER]:[PASS]@[HOST]/[DB]",
            ),
            (r"mysql://[^:]+:[^@]+@[^/]+/[^\s]+", "mysql://[USER]:[PASS]@[HOST]/[DB]"),
            (
                r"mongodb://[^:]+:[^@]+@[^/]+/[^\s]+",
                "mongodb://[USER]:[PASS]@[HOST]/[DB]",
            ),
            (r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", r"[EMAIL]@\2"),
            (r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}", r"\1[IP]"),
            (r"/home/[^/\s]+", "/home/[USER]"),
            (r"/Users/[^/\s]+", "/Users/[USER]"),
            (r"C:\\Users\\[^\\]+", r"C:\\Users\\[USER]"),
            (r"-----BEGIN [A-Z ]+-----.*?-----END [A-Z ]+-----", "[SSH_KEY]"),
            (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CREDIT_CARD]"),
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]"),
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
        ]

        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.DOTALL), replacement)
            for pattern, replacement in self.sensitive_patterns
        ]

        self.noise_patterns = [
            (r"(.)\1{50,}", lambda m: m.group(1) * 10 + "[...]"),
            (r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\xFF]{10,}", "[BINARY_DATA]"),
            (r"^.{500,}$", lambda m: m.group(0)[:500] + "[TRUNCATED]"),
        ]

        self.compiled_noise_patterns: List[Tuple[Any, Any]] = [
            (re.compile(pattern, re.MULTILINE), replacement)
            for pattern, replacement in self.noise_patterns
        ]

        self.sensitive_commands = {
            "env",
            "printenv",
            "set",  # Environment variables
            "history",  # Command history
            "cat",
            "less",
            "more",
            "head",
            "tail",  # File content (when reading sensitive files)
            "grep",  # When searching in sensitive files
            "ps",
            "top",  # Process lists (may contain sensitive args)
        }

        self.sensitive_extensions = {
            ".key",
            ".pem",
            ".p12",
            ".pfx",
            ".crt",
            ".cer",  # Certificates and keys
            ".env",
            ".config",
            ".conf",  # Configuration files
            ".sql",
            ".db",
            ".sqlite",  # Database files
            ".log",  # Log files (may contain sensitive data)
        }

        self.sensitive_directories = {
            ".ssh",
            ".gnupg",
            ".aws",
            ".config",
            "secrets",
            "private",
            "confidential",
            ".env",
            "credentials",
        }

    def filter_command_context(self, context: CommandContext) -> CommandContext:
        """Filter a command context to remove sensitive information."""

        filtered_command = self._filter_text(context.command)

        filtered_output = self._filter_output(context.output, context.command)
        filtered_error = self._filter_text(context.error)

        return replace(
            context,
            command=filtered_command,
            output=filtered_output,
            error=filtered_error,
        )

    def filter_text(self, text: str) -> str:
        """Public method to filter arbitrary text."""
        return self._filter_text(text)

    def _filter_text(self, text: str) -> str:
        """Apply all filtering patterns to text."""
        if not text:
            return text

        filtered = text

        for pattern, replacement in self.compiled_patterns:
            if callable(replacement):
                filtered = pattern.sub(replacement, filtered)
            else:
                filtered = pattern.sub(replacement, filtered)

        for pattern, replacement in self.compiled_noise_patterns:
            if callable(replacement):
                filtered = pattern.sub(replacement, filtered)
            else:
                filtered = pattern.sub(replacement, filtered)

        return filtered

    def _filter_output(self, output: str, command: str) -> str:
        """Filter output with command-specific context."""
        if not output:
            return output

        filtered = self._filter_text(output)

        command_parts = command.strip().split()
        if not command_parts:
            return filtered

        base_command = command_parts[0]

        if base_command in {"env", "printenv", "set"}:
            filtered = self._filter_env_output(filtered)

        elif base_command in {"cat", "less", "more", "head", "tail"}:
            if len(command_parts) > 1:
                filename = command_parts[1]
                if self._is_sensitive_file(filename):
                    filtered = "[SENSITIVE_FILE_CONTENT]"

        elif base_command in {"ps", "top"}:
            filtered = self._filter_process_output(filtered)

        elif base_command == "history":
            filtered = self._filter_history_output(filtered)

        if len(filtered) > 2000:
            filtered = filtered[:2000] + "\n[OUTPUT_TRUNCATED]"

        return filtered

    def _filter_env_output(self, output: str) -> str:
        """Filter environment variable output."""
        lines = output.split("\n")
        filtered_lines = []

        for line in lines:
            if "=" in line:
                var_name, var_value = line.split("=", 1)

                if any(
                    sensitive in var_name.upper()
                    for sensitive in [
                        "PASSWORD",
                        "SECRET",
                        "KEY",
                        "TOKEN",
                        "API",
                        "AUTH",
                        "CREDENTIAL",
                        "PRIVATE",
                        "PASS",
                    ]
                ):
                    filtered_lines.append(f"{var_name}=[FILTERED]")
                else:
                    filtered_value = self._filter_text(var_value)
                    filtered_lines.append(f"{var_name}={filtered_value}")
            else:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _filter_process_output(self, output: str) -> str:
        """Filter process list output to remove sensitive command arguments."""
        lines = output.split("\n")
        filtered_lines = []

        for line in lines:
            if any(
                sensitive in line.lower()
                for sensitive in ["password=", "secret=", "key=", "token=", "auth="]
            ):
                parts = line.split()
                if len(parts) > 0:
                    filtered_line = " ".join(parts[:2]) + " [FILTERED_ARGS]"
                    filtered_lines.append(filtered_line)
                else:
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _filter_history_output(self, output: str) -> str:
        """Filter command history output."""
        lines = output.split("\n")
        filtered_lines = []

        for line in lines:
            cleaned_line = re.sub(r"^\s*\d+\s+", "", line)

            filtered_command = self._filter_text(cleaned_line)

            if any(
                sensitive in cleaned_line.lower()
                for sensitive in ["password", "secret", "key", "token", "auth", "login"]
            ):
                filtered_lines.append("[SENSITIVE_COMMAND]")
            else:
                filtered_lines.append(filtered_command)

        return "\n".join(filtered_lines)

    def _is_sensitive_file(self, filename: str) -> bool:
        """Check if a filename suggests sensitive content."""
        filename_lower = filename.lower()

        for ext in self.sensitive_extensions:
            if filename_lower.endswith(ext):
                return True

        for sensitive_dir in self.sensitive_directories:
            if sensitive_dir in filename_lower:
                return True

        sensitive_patterns = [
            "password",
            "secret",
            "key",
            "token",
            "credential",
            "private",
            "confidential",
            "auth",
            "login",
        ]

        return any(pattern in filename_lower for pattern in sensitive_patterns)

    def add_sensitive_pattern(self, pattern: str, replacement: str):
        """Add a custom sensitive pattern."""
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE | re.DOTALL)
            self.compiled_patterns.append((compiled_pattern, replacement))
        except re.error as e:
            raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e

    def remove_sensitive_pattern(self, pattern: str) -> bool:
        """Remove a sensitive pattern."""
        for i, (compiled_pattern, _) in enumerate(self.compiled_patterns):
            if compiled_pattern.pattern == pattern:
                del self.compiled_patterns[i]
                return True
        return False

    def get_filter_statistics(self) -> Dict:
        """Get statistics about filtering patterns."""
        return {
            "sensitive_patterns": len(self.compiled_patterns),
            "noise_patterns": len(self.compiled_noise_patterns),
            "sensitive_commands": len(self.sensitive_commands),
            "sensitive_extensions": len(self.sensitive_extensions),
            "sensitive_directories": len(self.sensitive_directories),
        }
