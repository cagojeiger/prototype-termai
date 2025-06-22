#!/usr/bin/env python3
"""
Simple integration test for Phase 1 AI system integration
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_imports():
    """Test that all AI modules can be imported successfully."""
    try:
        from termai.ai.context_manager import ContextManager  # noqa: F401
        from termai.ai.ollama_client import create_ollama_client  # noqa: F401
        from termai.ai.realtime_analyzer import RealtimeAnalyzer  # noqa: F401

        print("✅ All AI modules import successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_context_manager():
    """Test context manager initialization."""
    try:
        from termai.ai.context_manager import ContextManager

        context_manager = ContextManager()  # noqa: F841
        print("✅ ContextManager initializes successfully")
        return True
    except Exception as e:
        print(f"❌ ContextManager error: {e}")
        return False


def test_terminal_manager_integration():
    """Test that TerminalManager accepts ai_analyzer parameter."""
    try:
        from termai.terminal.manager import TerminalManager

        manager = TerminalManager(ai_analyzer=None)  # noqa: F841
        print("✅ TerminalManager accepts ai_analyzer parameter")
        return True
    except Exception as e:
        print(f"❌ TerminalManager integration error: {e}")
        return False


def main():
    """Run integration tests."""
    print("🚀 Testing Phase 1 AI Integration\n")

    tests = [
        ("AI Module Imports", test_imports),
        ("Context Manager", test_context_manager),
        ("Terminal Manager Integration", test_terminal_manager_integration),
    ]

    passed = 0
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        if test_func():
            passed += 1
        print()

    print(f"Results: {passed}/{len(tests)} tests passed")

    if passed == len(tests):
        print("🎉 Phase 1 integration successful!")
        return True
    else:
        print("⚠️  Some integration tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
