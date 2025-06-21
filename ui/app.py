"""
Terminal AI Assistant - Main TUI Application

This module contains the main Textual application class that orchestrates
the terminal and AI sidebar components in a split-panel interface.
"""

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Header, Footer, Static


class TerminalAIApp(App):
    """Main Terminal AI Assistant TUI Application."""
    
    TITLE = "Terminal AI Assistant"
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_terminal", "Clear"),
        ("ctrl+a", "toggle_ai", "Toggle AI"),
        ("f1", "help", "Help"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        
        with Horizontal():
            yield Static("Terminal Area (65%)", classes="terminal-area")
            yield Static("AI Sidebar (35%)", classes="ai-sidebar")
            
        yield Footer()
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
    
    def action_clear_terminal(self) -> None:
        """Clear the terminal display."""
        pass
    
    def action_toggle_ai(self) -> None:
        """Toggle AI assistance on/off."""
        pass
    
    def action_help(self) -> None:
        """Show help information."""
        pass
