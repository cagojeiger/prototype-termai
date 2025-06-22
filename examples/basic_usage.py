#!/usr/bin/env python3
"""
Basic usage example for Terminal AI Assistant

This demonstrates how to use the Terminal AI Assistant programmatically.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from termai.ai.context_manager import ContextManager
from termai.ai.ollama_client import create_ollama_client
from termai.terminal.manager import TerminalManager


async def basic_terminal_example():
    """Basic example of using the terminal manager."""
    print("=== Basic Terminal Manager Example ===\n")

    # Create terminal manager
    tm = TerminalManager()

    # Set up output callback
    def handle_output(data: bytes):
        print(f"Output: {data.decode('utf-8', errors='replace')}")

    tm.emulator.on_output = handle_output

    # Start terminal
    tm.start()

    # Execute some commands
    commands = ["echo 'Hello from Terminal AI!'", "pwd", "date"]

    for cmd in commands:
        print(f"\nExecuting: {cmd}")
        tm.execute(cmd)
        await asyncio.sleep(1)

    # Stop terminal
    tm.stop()
    print("\nTerminal stopped.")


async def ai_integration_example():
    """Example with AI integration."""
    print("\n=== AI Integration Example ===\n")

    try:
        # Create AI client
        ollama_client = await create_ollama_client()

        # Check health
        is_healthy = await ollama_client.health_check()
        print(f"Ollama health: {'OK' if is_healthy else 'Not available'}")

        if is_healthy:
            # Create context manager
            context_manager = ContextManager()

            # Add some context
            context_manager.add_command_context(
                command="git push",
                directory="/home/user/project",
                exit_code=1,
                output="",
                error="error: failed to push some refs",
                duration=0.5,
            )

            # Get analysis context
            analysis_context = context_manager.get_analysis_context()
            print(f"\nAnalysis context: {analysis_context}")

        await ollama_client.close()

    except Exception as e:
        print(f"AI integration error: {e}")


async def main():
    """Run examples."""
    # Basic terminal example
    await basic_terminal_example()

    # AI integration example
    await ai_integration_example()


if __name__ == "__main__":
    print("Terminal AI Assistant - Basic Usage Examples\n")
    asyncio.run(main())
