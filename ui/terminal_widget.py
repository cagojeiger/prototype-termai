"""
Terminal Widget - Terminal Display Component

This module contains the terminal widget that displays terminal output
and handles user input in the 65% left panel of the application.
"""

from typing import TYPE_CHECKING, Optional

from rich.console import Console
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static

if TYPE_CHECKING:
    from terminal.buffer import OutputBuffer
    from terminal.emulator import TerminalEmulator
    from terminal.manager import TerminalManager
else:
    try:
        from terminal.buffer import OutputBuffer
        from terminal.emulator import TerminalEmulator
        from terminal.manager import TerminalManager
    except ImportError:
        TerminalManager = None
        TerminalEmulator = None
        OutputBuffer = None


class TerminalWidget(Static):
    """Terminal display widget (65% width)."""

    output = reactive("")
    cursor_position = reactive((0, 0))

    class TerminalOutput(Message):
        """Message sent when terminal produces output."""

        def __init__(self, output: str) -> None:
            self.output = output
            super().__init__()

    def __init__(self, test_mode: bool = False, ai_analyzer=None, **kwargs):
        """Initialize the terminal widget.

        Args:
            test_mode: If True, run without actual terminal integration
            ai_analyzer: Optional RealtimeAnalyzer instance for AI features
            **kwargs: Additional keyword arguments passed to Static
        """
        super().__init__(**kwargs)
        self.test_mode = test_mode
        self.ai_analyzer = ai_analyzer
        self.terminal_manager: Optional[TerminalManager] = None
        self.console = Console()

        if not test_mode and TerminalManager is not None:
            try:
                self.terminal_manager = TerminalManager(ai_analyzer=ai_analyzer)
            except Exception as e:
                self.log(f"Failed to initialize terminal manager: {e}")
                self.test_mode = True

    def compose(self):
        """Compose the terminal widget."""
        if self.test_mode:
            initial_text = """
🖥️  터미널 위젯 (테스트 모드)

$ echo "Hello from Terminal Widget!"
Hello from Terminal Widget!

$ pwd
/home/ubuntu/repos/prototype-termai

$ ls -la
total 24
drwxr-xr-x  8 ubuntu ubuntu 4096 Jun 21 14:33 .
drwxr-xr-x  4 ubuntu ubuntu 4096 Jun 21 14:30 ..
-rw-r--r--  1 ubuntu ubuntu 1234 Jun 21 14:33 main.py
drwxr-xr-x  2 ubuntu ubuntu 4096 Jun 21 14:33 ui/
drwxr-xr-x  2 ubuntu ubuntu 4096 Jun 21 14:30 terminal/

$ _
            """
        else:
            initial_text = "터미널 초기화 중..."

        return [Static(initial_text, id="terminal-output")]

    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        if not self.test_mode and self.terminal_manager:
            self._start_terminal()

        self.can_focus = True

    def _start_terminal(self) -> None:
        """Start the terminal manager in background."""
        try:
            if self.terminal_manager:
                self.terminal_manager.start()
                self._monitor_output()
        except Exception as e:
            self.log(f"Failed to start terminal: {e}")
            self.test_mode = True

    def _monitor_output(self) -> None:
        """Monitor terminal output and update display."""
        if not self.terminal_manager:
            return

        def update_output():
            try:
                if self.terminal_manager:
                    output = self.terminal_manager.get_plain_output(50)
                    if output:
                        self.update_display(output)
            except Exception as e:
                self.log(f"Error monitoring output: {e}")

        self.set_interval(0.1, update_output)

    def update_display(self, output: str) -> None:
        """Update the terminal display with new output."""
        terminal_output = self.query_one("#terminal-output", Static)

        processed_output = self._process_ansi_output(output)
        terminal_output.update(processed_output)

        self.scroll_end()

    def _process_ansi_output(self, output: str) -> str:
        """Process ANSI escape sequences in terminal output."""
        return output

    def on_key(self, event) -> None:
        """Handle keyboard input."""
        if self.test_mode:
            self._handle_test_input(event.key)
        elif self.terminal_manager:
            try:
                self.terminal_manager.write_text(event.key)
            except Exception as e:
                self.log(f"Error sending input: {e}")

    def _handle_test_input(self, key: str) -> None:
        """Handle input in test mode."""
        terminal_output = self.query_one("#terminal-output", Static)
        current_text = terminal_output.renderable

        if key == "enter":
            new_text = f"{current_text}\n$ "
        elif key == "backspace":
            lines = str(current_text).split("\n")
            if lines and lines[-1].endswith("$ "):
                return
            if lines:
                lines[-1] = lines[-1][:-1] if len(lines[-1]) > 2 else lines[-1]
            new_text = "\n".join(lines)
        elif len(key) == 1:
            new_text = f"{current_text}{key}"
        else:
            return

        terminal_output.update(new_text)
        self.scroll_end()

    def clear(self) -> None:
        """Clear the terminal display."""
        if self.test_mode:
            terminal_output = self.query_one("#terminal-output", Static)
            terminal_output.update("$ ")
        elif self.terminal_manager:
            try:
                self.terminal_manager.clear_screen()
            except Exception as e:
                self.log(f"Error clearing terminal: {e}")

    def on_focus(self) -> None:
        """Called when the widget gains focus."""
        self.add_class("focused")

    def on_blur(self) -> None:
        """Called when the widget loses focus."""
        self.remove_class("focused")
