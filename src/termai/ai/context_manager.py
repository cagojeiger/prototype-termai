"""
Context Manager for Terminal AI Assistant

This module orchestrates context collection, filtering, and management
for AI analysis by coordinating between different context sources.
"""

import asyncio
import time
from dataclasses import dataclass

from .context import CommandContext, ContextWindow, SessionContext, classify_command
from .filters import ContextFilter
from .triggers import Trigger, TriggerManager


@dataclass
class AIAnalysisRequest:
    """Request for AI analysis with context and metadata."""

    trigger: Trigger
    context: CommandContext
    session_context: SessionContext
    relevant_history: list[CommandContext]
    priority: int
    timestamp: float
    request_id: str


class ContextManager:
    """Orchestrates context collection and management for AI analysis."""

    def __init__(self, max_context_length: int = 4000):
        self.context_window = ContextWindow(max_tokens=max_context_length)
        self.trigger_manager = TriggerManager()
        self.context_filter = ContextFilter()

        self.analysis_queue: asyncio.Queue = asyncio.Queue()
        self.active_requests: dict[str, AIAnalysisRequest] = {}

        self.stats = {
            "commands_processed": 0,
            "triggers_fired": 0,
            "analysis_requests": 0,
            "context_compressions": 0,
        }

        self.config = {
            "max_queue_size": 50,
            "context_compression_threshold": 0.8,
            "auto_cleanup_interval": 300,  # 5 minutes
        }

        self._last_cleanup = time.time()

    async def process_command(
        self,
        command: str,
        directory: str,
        exit_code: int,
        output: str,
        error: str,
        duration: float,
    ) -> AIAnalysisRequest | None:
        """Process a new command and determine if AI analysis is needed."""

        command_type = classify_command(command)
        context = CommandContext(
            command=command,
            directory=directory,
            timestamp=time.time(),
            exit_code=exit_code,
            output=output,
            error=error,
            duration=duration,
            command_type=command_type,
        )

        context = self.context_filter.filter_command_context(context)

        self.context_window.add_command(context)
        self.stats["commands_processed"] += 1

        self._update_session_context(context)

        triggered = self.trigger_manager.evaluate_command(context)

        if triggered:
            self.stats["triggers_fired"] += len(triggered)

            highest_priority_trigger = triggered[0]
            request = await self._create_analysis_request(
                highest_priority_trigger, context
            )

            if self.analysis_queue.qsize() < self.config["max_queue_size"]:
                await self.analysis_queue.put(request)
                self.active_requests[request.request_id] = request
                self.stats["analysis_requests"] += 1
                return request

        await self._periodic_cleanup()

        return None

    async def process_manual_request(self, request_text: str) -> AIAnalysisRequest:
        """Process a manual AI analysis request from user."""

        triggers = self.trigger_manager.evaluate_manual_request(request_text)
        manual_trigger = triggers[0] if triggers else None

        if not manual_trigger:
            raise ValueError("Failed to create manual trigger")

        dummy_context = CommandContext(
            command=f"[MANUAL REQUEST] {request_text}",
            directory=self.context_window.session.current_directory,
            timestamp=time.time(),
            exit_code=0,
            output="",
            error="",
            duration=0.0,
            command_type=classify_command(""),
        )

        request = await self._create_analysis_request(manual_trigger, dummy_context)

        await self.analysis_queue.put(request)
        self.active_requests[request.request_id] = request
        self.stats["analysis_requests"] += 1

        return request

    async def get_next_analysis_request(self) -> AIAnalysisRequest | None:
        """Get the next analysis request from the queue."""
        try:
            request: AIAnalysisRequest = await asyncio.wait_for(
                self.analysis_queue.get(), timeout=1.0
            )
            return request
        except TimeoutError:
            return None

    def complete_analysis_request(self, request_id: str):
        """Mark an analysis request as completed."""
        if request_id in self.active_requests:
            del self.active_requests[request_id]

    def get_context_summary(self) -> str:
        """Get a summary of current context for debugging."""
        return self.context_window.get_context_summary()

    def get_relevant_context(
        self, max_tokens: int | None = None
    ) -> list[CommandContext]:
        """Get relevant context for AI analysis."""
        return self.context_window.get_relevant_context(max_tokens)

    def update_session_info(self, **kwargs):
        """Update session context information."""
        self.context_window.update_session_context(**kwargs)

    def get_statistics(self) -> dict:
        """Get comprehensive statistics about context management."""
        context_stats = self.context_window.get_statistics()
        trigger_stats = self.trigger_manager.get_trigger_statistics()

        return {
            **self.stats,
            "context_window": context_stats,
            "triggers": trigger_stats,
            "queue_size": self.analysis_queue.qsize(),
            "active_requests": len(self.active_requests),
        }

    def configure(self, **kwargs):
        """Update configuration settings."""
        self.config.update(kwargs)

    async def _create_analysis_request(
        self, trigger: Trigger, context: CommandContext
    ) -> AIAnalysisRequest:
        """Create an AI analysis request with relevant context."""

        relevant_history = self.context_window.get_relevant_context()

        if self._should_compress_context(relevant_history):
            relevant_history = await self._compress_context(relevant_history)
            self.stats["context_compressions"] += 1

        request_id = f"{trigger.name}_{int(time.time() * 1000)}"

        return AIAnalysisRequest(
            trigger=trigger,
            context=context,
            session_context=self.context_window.session,
            relevant_history=relevant_history,
            priority=trigger.priority,
            timestamp=time.time(),
            request_id=request_id,
        )

    def _update_session_context(self, context: CommandContext):
        """Update session context based on command execution."""

        if context.command.strip().startswith("cd ") and context.exit_code == 0:
            parts = context.command.strip().split()
            if len(parts) > 1:
                new_dir = parts[1]
                if new_dir.startswith("/"):
                    self.context_window.session.current_directory = new_dir
                elif new_dir == "..":
                    current = self.context_window.session.current_directory
                    parent = "/".join(current.rstrip("/").split("/")[:-1]) or "/"
                    self.context_window.session.current_directory = parent

        if context.command.startswith("git ") and "status" in context.command:
            if context.exit_code == 0:
                output_lines = context.output.split("\n")
                branch = "main"  # default
                has_changes = False

                for line in output_lines:
                    if line.startswith("On branch "):
                        branch = line.replace("On branch ", "").strip()
                    elif "nothing to commit" in line:
                        has_changes = False
                    elif any(
                        keyword in line
                        for keyword in ["modified:", "new file:", "deleted:"]
                    ):
                        has_changes = True

                self.context_window.session.update_git_status(
                    branch=branch,
                    status="clean" if not has_changes else "modified",
                    has_changes=has_changes,
                )

    def _should_compress_context(self, context_list: list[CommandContext]) -> bool:
        """Determine if context compression is needed."""
        total_tokens = (
            sum(
                len(ctx.command) + len(ctx.output) + len(ctx.error)
                for ctx in context_list
            )
            // 4
        )  # Rough token estimation

        threshold = (
            self.context_window.max_tokens
            * self.config["context_compression_threshold"]
        )
        return total_tokens > threshold

    async def _compress_context(
        self, context_list: list[CommandContext]
    ) -> list[CommandContext]:
        """Compress context by removing less relevant commands."""

        sorted_context = sorted(
            context_list, key=lambda x: x.relevance_score, reverse=True
        )

        keep_count = max(1, int(len(sorted_context) * 0.7))
        compressed = sorted_context[:keep_count]

        compressed.sort(key=lambda x: x.timestamp)

        return compressed

    async def _periodic_cleanup(self):
        """Perform periodic cleanup of old data."""
        current_time = time.time()

        if current_time - self._last_cleanup > self.config["auto_cleanup_interval"]:
            cutoff_time = current_time - 3600  # 1 hour ago

            expired_requests = [
                req_id
                for req_id, req in self.active_requests.items()
                if req.timestamp < cutoff_time
            ]

            for req_id in expired_requests:
                del self.active_requests[req_id]

            self.trigger_manager.clear_history()

            self._last_cleanup = current_time

    def clear_all_context(self):
        """Clear all context data (for testing or reset)."""
        self.context_window.clear()
        self.trigger_manager.clear_history()
        self.active_requests.clear()

        while not self.analysis_queue.empty():
            try:
                self.analysis_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        self.stats = {
            "commands_processed": 0,
            "triggers_fired": 0,
            "analysis_requests": 0,
            "context_compressions": 0,
        }
