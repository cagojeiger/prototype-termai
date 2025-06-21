#!/usr/bin/env python3
"""
Terminal AI Assistant - Main Entry Point

This is the primary entry point for the Terminal AI Assistant application.
It initializes and runs the Textual TUI application.
"""

from ui.app import TerminalAIApp


def main():
    """Main entry point for the Terminal AI Assistant."""
    app = TerminalAIApp()
    app.run()


if __name__ == "__main__":
    main()
