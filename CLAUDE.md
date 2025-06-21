# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

prototype-termai is a Terminal AI Assistant that provides real-time AI-powered assistance for terminal operations using local LLM models through Ollama. The system watches terminal activity and offers contextual help, error solutions, and command suggestions in a non-intrusive sidebar.

## Key Architecture Components

### Core System Design
- **PTY-based Terminal Emulation**: Uses Python's `pty` module to create a fully functional terminal wrapper that captures all input/output while maintaining complete shell compatibility
- **Async Event-Driven Architecture**: Built on asyncio with an event bus system to ensure terminal operations are never blocked by AI processing
- **Smart Context Management**: Implements relevance scoring and context compression to work within Ollama's token limits (4K-8K tokens)
- **Real-time UI Updates**: Textual framework with separate terminal panel (65%) and AI sidebar (35%) that updates asynchronously

### Module Structure
```
terminal/    - Terminal emulation (TerminalEmulator, OutputBuffer, CommandHistory)
ui/          - TUI components (TerminalAIApp, TerminalWidget, AISidebar)
ai/          - AI integration (OllamaClient, ContextManager, TriggerManager)
utils/       - Core utilities (EventBus, PerformanceProfiler, MemoryManager)
```

## Development Commands

### Initial Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and create virtual environment
uv sync

# Install Ollama and models
ollama serve  # Run in separate terminal
ollama pull codellama:7b

# Set up pre-commit hooks
uv run pre-commit install

# Create project structure (if needed)
mkdir -p terminal ui ai utils tests
```

### Running Tests
```bash
# Test terminal wrapper
uv run python test_terminal.py

# Test UI components
uv run python test_ui.py

# Test Ollama integration
uv run python test_ollama.py

# Test context management
uv run python test_context.py

# Run all tests (once implemented)
uv run pytest tests/

# Run pre-commit checks
uv run pre-commit run --all-files
```

### Running the Application
```bash
# Basic run
uv run python main.py

# With debugging
uv run python main.py --debug --log-level=DEBUG

# Performance profiling
uv run python -m cProfile -o profile.stats main.py
```

## Critical Implementation Details

### Terminal Output Processing
The terminal emulator must handle ANSI escape sequences, UTF-8 encoding, and special characters. Output is captured in a circular buffer with configurable size limits. Command detection relies on prompt pattern matching (configurable for different shells).

### AI Triggering Logic
AI analysis triggers on:
- Command execution errors (exit code != 0)
- Dangerous command patterns (rm -rf, sudo rm)
- Specific error patterns in output
- Manual user requests

The trigger system uses priority queuing to handle multiple simultaneous events without overwhelming the LLM.

### Context Window Management
Context is managed through a sliding window approach with relevance scoring:
- Error commands: score 0.9
- Git/npm/docker commands: score 0.7-0.8
- Navigation commands (ls, cd): score 0.3
- Important commands are preserved beyond the sliding window

### Performance Optimization Strategies
- Response caching with TTL and LRU eviction
- API throttling (5 requests/second default)
- Background prefetching for common errors
- Memory cleanup every 5 minutes
- Command output filtering to remove noise

## Environment Configuration

Create `.env` file with:
```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=codellama:7b
OLLAMA_TIMEOUT=30
APP_LOG_LEVEL=INFO
AI_MAX_CONTEXT_LENGTH=20
AI_RESPONSE_MAX_TOKENS=500
```

## Common Development Tasks

### Adding a New AI Trigger
1. Add trigger pattern to `ai/triggers.py` in `_init_default_triggers()`
2. Set appropriate priority (1-10, higher = more important)
3. Test with `test_triggers()` in `test_ollama.py`

### Modifying UI Layout
1. Update CSS in `ui/app.py` for layout percentages
2. Adjust widget sizing in respective widget files
3. Test responsiveness with terminal resizing

### Debugging AI Responses
1. Enable debug logging: `export LOG_LEVEL=DEBUG`
2. Check raw Ollama responses in logs
3. Use `test_ollama.py` to test specific contexts
4. Monitor `/api/generate` calls with network tools

## Implementation Checkpoints

Follow the numbered plan files in order:
1. `plan/01-setup.md` - Environment setup
2. `plan/02-basic-terminal.md` - Terminal wrapper
3. `plan/03-tui-framework.md` - UI implementation
4. `plan/04-ollama-integration.md` - AI integration
5. `plan/05-context-management.md` - Context system
6. `plan/06-realtime-features.md` - Async features
7. `plan/07-optimization.md` - Performance tuning

Each major component has a corresponding checkpoint in `plan/checkpoints/` for validation.
