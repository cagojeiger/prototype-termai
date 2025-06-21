#!/usr/bin/env python3
"""
Terminal AI Assistant - Main Entry Point

This is the primary entry point for the Terminal AI Assistant application.
It initializes the AI system and runs the Textual TUI application.
"""

import asyncio
import sys
from typing import Optional

from ai.ollama_client import create_ollama_client
from ai.context_manager import ContextManager
from ai.realtime_analyzer import RealtimeAnalyzer
from ui.app import TerminalAIApp


async def create_ai_system() -> Optional[RealtimeAnalyzer]:
    """Create and initialize the AI system components.
    
    Returns:
        RealtimeAnalyzer instance if successful, None if failed.
    """
    try:
        print("🔍 Initializing AI system...")
        
        ollama_client = await create_ollama_client()
        
        is_healthy = await ollama_client.health_check()
        if not is_healthy:
            print("⚠️  Ollama server not available. AI features will be disabled.")
            print("   Start Ollama with: ollama serve")
            await ollama_client.close()
            return None
        
        models = await ollama_client.list_models()
        if not models:
            print("⚠️  No Ollama models found. AI features will be disabled.")
            print("   Install a model with: ollama pull codellama:7b")
            await ollama_client.close()
            return None
        
        print(f"✅ Connected to Ollama with {len(models)} model(s)")
        
        context_manager = ContextManager()
        analyzer = RealtimeAnalyzer(ollama_client, context_manager)
        
        await analyzer.start()
        print("✅ AI system initialized successfully")
        
        return analyzer
        
    except Exception as e:
        print(f"❌ Failed to initialize AI system: {e}")
        print("   AI features will be disabled")
        return None


async def async_main():
    """Async main entry point for the Terminal AI Assistant."""
    ai_analyzer = await create_ai_system()
    
    app = TerminalAIApp(ai_analyzer=ai_analyzer)
    
    try:
        app.run()
    finally:
        if ai_analyzer:
            print("🔄 Shutting down AI system...")
            await ai_analyzer.stop()
            await ai_analyzer.ollama_client.close()
            print("✅ AI system shutdown complete")


def main():
    """Main entry point for the Terminal AI Assistant."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n👋 Terminal AI Assistant stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
