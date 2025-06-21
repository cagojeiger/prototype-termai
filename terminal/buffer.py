import re
from collections import deque
from typing import List, Tuple


class OutputBuffer:
    """Terminal output buffer with ANSI escape sequence processing"""

    def __init__(self, max_lines: int = 1000):
        self.max_lines = max_lines
        self.lines: deque = deque(maxlen=max_lines)
        self.current_line = ""

        self.ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

        self.control_chars = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")

    def append(self, data: bytes):
        """Add new data to the buffer"""
        try:
            text = data.decode("utf-8", errors="replace")
        except UnicodeDecodeError:
            text = data.decode("latin-1", errors="replace")

        for char in text:
            if char == "\n":
                self._add_line(self.current_line)
                self.current_line = ""
            elif char == "\r":
                self.current_line = ""
            elif char == "\b":
                if self.current_line:
                    self.current_line = self.current_line[:-1]
            elif char == "\t":
                spaces_needed = 8 - (len(self.current_line) % 8)
                self.current_line += " " * spaces_needed
            elif ord(char) >= 32 or char in "\t\n":
                self.current_line += char

    def _add_line(self, line: str):
        """Add a complete line to the buffer"""
        cleaned_line = self._clean_line(line)
        self.lines.append(cleaned_line)

    def _clean_line(self, line: str) -> str:
        """Clean a line by removing unwanted control characters"""
        cleaned = self.control_chars.sub("", line)
        return cleaned.rstrip()  # Remove trailing whitespace

    def get_lines(self, count: int = -1) -> List[str]:
        """Get lines from the buffer"""
        if count == -1:
            result = list(self.lines)
            if self.current_line:
                result.append(self.current_line)
            return result
        else:
            all_lines = list(self.lines)
            if self.current_line:
                all_lines.append(self.current_line)
            return all_lines[-count:] if count > 0 else all_lines[:count]

    def get_plain_text(self, count: int = -1) -> str:
        """Get plain text with ANSI escape sequences removed"""
        lines = self.get_lines(count)
        plain_lines = []

        for line in lines:
            plain_line = self.ansi_escape.sub("", line)
            plain_lines.append(plain_line)

        return "\n".join(plain_lines)

    def get_recent_lines(self, count: int = 10) -> List[str]:
        """Get the most recent lines"""
        return self.get_lines(count)

    def clear(self):
        """Clear the buffer"""
        self.lines.clear()
        self.current_line = ""

    def search(
        self, pattern: str, case_sensitive: bool = False
    ) -> List[Tuple[int, str]]:
        """Search for pattern in buffer lines"""
        results = []
        lines = list(self.lines)

        if self.current_line:
            lines.append(self.current_line)

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            search_regex = re.compile(pattern, flags)
        except re.error:
            pattern_escaped = re.escape(pattern)
            search_regex = re.compile(pattern_escaped, flags)

        for i, line in enumerate(lines):
            plain_line = self.ansi_escape.sub("", line)
            if search_regex.search(line) or search_regex.search(plain_line):
                results.append((i, line))

        return results

    def get_line_count(self) -> int:
        """Get total number of lines in buffer"""
        count = len(self.lines)
        if self.current_line:
            count += 1
        return count

    def get_last_line(self) -> str:
        """Get the last complete line"""
        if self.lines:
            return str(self.lines[-1])
        return ""

    def get_current_line(self) -> str:
        """Get the current incomplete line"""
        return self.current_line

    def has_ansi_codes(self, text: str) -> bool:
        """Check if text contains ANSI escape sequences"""
        return bool(self.ansi_escape.search(text))

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from text"""
        return self.ansi_escape.sub("", text)

    def get_buffer_info(self) -> dict:
        """Get buffer statistics"""
        return {
            "total_lines": len(self.lines),
            "max_lines": self.max_lines,
            "current_line_length": len(self.current_line),
            "buffer_full": len(self.lines) >= self.max_lines,
        }

    def flush_current_line(self):
        """Force the current line to be added to buffer"""
        if self.current_line:
            self._add_line(self.current_line)
            self.current_line = ""
