"""
Terminal AI Assistant - Main TUI Application

This module contains the main Textual application class that orchestrates
the terminal and AI sidebar components in a split-panel interface.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Static
from .terminal_widget import TerminalWidget
from .ai_sidebar import AISidebar


class TerminalAIApp(App):
    """Main Terminal AI Assistant TUI Application."""
    
    TITLE = "Terminal AI Assistant"
    
    CSS = """
    .terminal-area {
        width: 65%;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    .ai-sidebar {
        width: 35%;
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }
    
    Header {
        dock: top;
        height: 3;
    }
    
    Footer {
        dock: bottom;
        height: 1;
    }
    """
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_terminal", "Clear"),
        ("ctrl+a", "toggle_ai", "Toggle AI"),
        ("f1", "help", "Help"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        
        with Horizontal(id="main-container"):
            yield TerminalWidget(test_mode=True, classes="terminal-area")
            yield AISidebar(classes="ai-sidebar")
            
        yield Footer()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_clear_terminal(self) -> None:
        """Clear the terminal display."""
        try:
            terminal_widget = self.query_one(TerminalWidget)
            terminal_widget.clear()
        except Exception as e:
            self.log(f"Error clearing terminal: {e}")
    
    def action_toggle_ai(self) -> None:
        """Toggle AI assistance on/off."""
        try:
            ai_sidebar = self.query_one(AISidebar)
            ai_sidebar.set_ai_status(not ai_sidebar.ai_status)
        except Exception as e:
            self.log(f"Error toggling AI: {e}")
    
    def action_help(self) -> None:
        """Show help information."""
        pass
