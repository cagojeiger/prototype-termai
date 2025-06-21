"""
Test script for Ollama AI integration

This script tests the AI modules and integration with Ollama server.
Run this to verify Checkpoint 3 implementation.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai.context_manager import ContextManager
from ai.ollama_client import create_ollama_client
from ai.realtime_analyzer import RealtimeAnalyzer


async def test_ollama_connection():
    """Test basic Ollama server connection."""
    print("🔍 Testing Ollama connection...")

    try:
        client = await create_ollama_client()

        is_healthy = await client.health_check()
        print(f"   Health check: {'✅ PASS' if is_healthy else '❌ FAIL'}")

        if not is_healthy:
            print("   ⚠️  Ollama server not running. Start with: ollama serve")
            return False

        models = await client.list_models()
        print(f"   Available models: {len(models)}")
        for model in models[:3]:  # Show first 3
            print(f"     - {model}")

        if not models:
            print("   ⚠️  No models found. Install with: ollama pull codellama:7b")
            return False

        await client.close()
        return True

    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False


async def test_ai_analysis():
    """Test AI analysis functionality."""
    print("\n🧠 Testing AI analysis...")

    try:
        client = await create_ollama_client()

        print("   Testing error analysis...")
        response = await client.analyze_command_error(
            command="ls /nonexistent",
            error_output="ls: cannot access '/nonexistent': No such file or directory",
        )

        print(f"   Response length: {len(response.content)} chars")
        print(f"   Suggestions: {len(response.suggestions)}")
        print(f"   Confidence: {response.confidence:.2f}")
        print(f"   Response time: {response.response_time:.2f}s")

        if response.suggestions:
            print(f"   First suggestion: {response.suggestions[0][:50]}...")

        await client.close()
        return True

    except Exception as e:
        print(f"   ❌ Analysis failed: {e}")
        return False


async def test_context_management():
    """Test context management system."""
    print("\n📝 Testing context management...")

    try:
        context_manager = ContextManager()

        test_commands = [
            (
                "ls -la",
                "/home/user",
                0,
                "total 8\ndrwxr-xr-x 2 user user 4096",
                "",
                0.1,
            ),
            (
                "cd /nonexistent",
                "/home/user",
                1,
                "",
                "cd: /nonexistent: No such file or directory",
                0.05,
            ),
            (
                "git status",
                "/home/user/project",
                0,
                "On branch main\nnothing to commit",
                "",
                0.2,
            ),
        ]

        for cmd, dir, exit_code, output, error, duration in test_commands:
            request = await context_manager.process_command(
                command=cmd,
                directory=dir,
                exit_code=exit_code,
                output=output,
                error=error,
                duration=duration,
            )

            if request:
                print(
                    f"   Triggered: {request.trigger.name} (priority {request.priority})"
                )

        relevant_context = context_manager.get_relevant_context()
        print(f"   Relevant context: {len(relevant_context)} commands")

        stats = context_manager.get_statistics()
        print(f"   Commands processed: {stats['commands_processed']}")
        print(f"   Triggers fired: {stats['triggers_fired']}")

        return True

    except Exception as e:
        print(f"   ❌ Context management failed: {e}")
        return False


async def test_realtime_analyzer():
    """Test real-time analyzer integration."""
    print("\n⚡ Testing real-time analyzer...")

    try:
        client = await create_ollama_client()
        context_manager = ContextManager()
        analyzer = RealtimeAnalyzer(client, context_manager)

        await analyzer.start()

        response = await analyzer.analyze_command_error(
            command="rm /important/file",
            error_output="rm: cannot remove '/important/file': Permission denied",
        )

        print(f"   Analysis completed in {response.response_time:.2f}s")
        print(f"   Suggestions provided: {len(response.suggestions)}")

        cached_response = await analyzer.analyze_command_error(
            command="rm /important/file",
            error_output="rm: cannot remove '/important/file': Permission denied",
        )

        print(f"   Cached response time: {cached_response.response_time:.2f}s")

        metrics = analyzer.get_metrics()
        print(f"   Cache hit rate: {metrics['cache_hit_rate']:.2f}")
        print(f"   Requests processed: {metrics['requests_processed']}")

        await analyzer.stop()
        await client.close()

        return True

    except Exception as e:
        print(f"   ❌ Real-time analyzer failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Testing Checkpoint 3: Ollama AI Integration\n")

    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("AI Analysis", test_ai_analysis),
        ("Context Management", test_context_management),
        ("Real-time Analyzer", test_realtime_analyzer),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! Checkpoint 3 is ready.")
    else:
        print("⚠️  Some tests failed. Check Ollama setup and dependencies.")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
