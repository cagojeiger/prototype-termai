#!/usr/bin/env python3
"""
Test UI Components - Basic TUI Testing

This module contains tests for the Terminal AI Assistant TUI components.
"""

from ui.ai_sidebar import AISidebar
from ui.app import TerminalAIApp
from ui.terminal_widget import TerminalWidget


def test_app_creation():
    """Test that the main app can be created."""
    app = TerminalAIApp()
    assert app.title == "Terminal AI Assistant"


def test_layout_composition():
    """Test app layout composition."""
    app = TerminalAIApp()
    assert ".terminal-area" in app.CSS
    assert ".ai-sidebar" in app.CSS
    assert "width: 65%" in app.CSS
    assert "width: 35%" in app.CSS

    binding_keys = [binding[0] for binding in app.BINDINGS]
    assert "ctrl+c" in binding_keys
    assert "ctrl+l" in binding_keys
    assert "ctrl+a" in binding_keys
    assert "f1" in binding_keys
    assert "tab" in binding_keys


def test_keyboard_shortcuts():
    """Test keyboard shortcut actions."""
    app = TerminalAIApp()

    assert hasattr(app, "action_quit")
    assert hasattr(app, "action_clear_terminal")
    assert hasattr(app, "action_toggle_ai")
    assert hasattr(app, "action_help")
    assert hasattr(app, "action_focus_next")


def test_terminal_widget_creation():
    """Test that terminal widget can be created."""
    widget = TerminalWidget(test_mode=True)
    assert widget.test_mode is True
    assert widget.terminal_manager is None


def test_ai_sidebar_creation():
    """Test that AI sidebar can be created."""
    sidebar = AISidebar()
    assert sidebar.message_count == 0
    assert len(sidebar.messages) == 0


def test_ai_sidebar_message_handling():
    """Test AI sidebar message functionality."""
    sidebar = AISidebar()

    sidebar.messages.append(("12:00:00", "Test", "This is a test message"))
    sidebar.message_count = 1
    assert sidebar.message_count == 1
    assert len(sidebar.messages) == 1

    sidebar.messages.clear()
    sidebar.message_count = 0
    assert sidebar.message_count == 0
    assert len(sidebar.messages) == 0


def test_ai_sidebar_basic_functionality():
    """Test AI sidebar basic functionality without DOM operations."""
    sidebar = AISidebar()

    assert sidebar is not None
    assert hasattr(sidebar, "messages")
    assert hasattr(sidebar, "message_count")
    assert hasattr(sidebar, "ai_status")


if __name__ == "__main__":
    print("🧪 Running UI Component Tests...")

    try:
        test_app_creation()
        print("✅ App creation test passed")

        test_layout_composition()
        print("✅ Layout composition test passed")

        test_keyboard_shortcuts()
        print("✅ Keyboard shortcuts test passed")

        test_terminal_widget_creation()
        print("✅ Terminal widget creation test passed")

        test_ai_sidebar_creation()
        print("✅ AI sidebar creation test passed")

        test_ai_sidebar_message_handling()
        print("✅ AI sidebar message handling test passed")

        test_ai_sidebar_basic_functionality()
        print("✅ AI sidebar basic functionality test passed")

        print("\n🎉 All UI component tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)

    print("\n💡 To run the actual TUI application:")
    print("   uv run python main.py")
    print("   uv run python main.py --test-mode")
    print("   uv run python main.py --debug")
