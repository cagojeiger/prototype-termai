"""
Real-time AI Analyzer for Terminal AI Assistant

This module provides asynchronous AI request processing with caching,
throttling, and background analysis capabilities.
"""

import asyncio
import hashlib
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .context_manager import AIAnalysisRequest, ContextManager
from .ollama_client import AIResponse, OllamaClient
from .prompts import PromptTemplate


@dataclass
class CachedResponse:
    """Cached AI response with metadata."""

    response: AIResponse
    timestamp: float
    hit_count: int
    ttl: float  # Time to live in seconds


class RealtimeAnalyzer:
    """Asynchronous AI request processing with caching and throttling."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        context_manager: ContextManager,
        max_concurrent_requests: int = 3,
        request_rate_limit: float = 5.0,  # requests per second
        cache_ttl: int = 300,  # 5 minutes
    ):
        self.ollama_client = ollama_client
        self.context_manager = context_manager
        self.max_concurrent_requests = max_concurrent_requests
        self.request_rate_limit = request_rate_limit
        self.cache_ttl = cache_ttl

        self.active_requests: dict[str, asyncio.Task] = {}
        self.request_semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.rate_limiter = asyncio.Semaphore(1)
        self.last_request_time = 0.0

        self.response_cache: dict[str, CachedResponse] = {}
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}

        self.background_tasks: list[asyncio.Task] = []
        self.is_running = False

        self.callbacks: dict[str, list[Callable]] = defaultdict(list)

        self.metrics = {
            "requests_processed": 0,
            "requests_failed": 0,
            "average_response_time": 0.0,
            "cache_hit_rate": 0.0,
            "active_requests": 0,
        }

    async def start(self):
        """Start the real-time analyzer background tasks."""
        if self.is_running:
            return

        self.is_running = True

        self.background_tasks.append(
            asyncio.create_task(self._process_analysis_requests())
        )

        self.background_tasks.append(asyncio.create_task(self._cache_cleanup_loop()))

        self.background_tasks.append(asyncio.create_task(self._update_metrics_loop()))

    async def stop(self):
        """Stop the real-time analyzer and cleanup resources."""
        self.is_running = False

        for task in self.background_tasks:
            task.cancel()

        await asyncio.gather(*self.background_tasks, return_exceptions=True)
        self.background_tasks.clear()

        for task in self.active_requests.values():
            task.cancel()

        await asyncio.gather(*self.active_requests.values(), return_exceptions=True)
        self.active_requests.clear()

    async def analyze_command_error(
        self, command: str, error_output: str, context: str | None = None
    ) -> AIResponse:
        """Analyze command error with caching and rate limiting."""

        cache_key = self._create_cache_key(
            "error", command, error_output, context or ""
        )

        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        await self._rate_limit()

        recent_commands = self.context_manager.get_relevant_context(max_tokens=1000)
        prompt = PromptTemplate.error_analysis_prompt(
            command=command,
            error_output=error_output,
            context=context,
            recent_commands=recent_commands,
        )

        async with self.request_semaphore:
            try:
                response = await self.ollama_client.generate(prompt)
                self._cache_response(cache_key, response)
                self.metrics["requests_processed"] += 1

                await self._trigger_callbacks(
                    "error_analyzed", {"command": command, "response": response}
                )

                return response

            except Exception as e:
                self.metrics["requests_failed"] += 1
                raise e

    async def analyze_command_output(
        self, command: str, output: str, context: str | None = None
    ) -> AIResponse:
        """Analyze successful command output."""

        cache_key = self._create_cache_key("output", command, output, context or "")

        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        await self._rate_limit()

        session_context = self.context_manager.context_window.session
        prompt = PromptTemplate.output_analysis_prompt(
            command=command, output=output, session_context=session_context
        )

        async with self.request_semaphore:
            try:
                response = await self.ollama_client.generate(prompt)
                self._cache_response(cache_key, response)
                self.metrics["requests_processed"] += 1

                await self._trigger_callbacks(
                    "output_analyzed", {"command": command, "response": response}
                )

                return response

            except Exception as e:
                self.metrics["requests_failed"] += 1
                raise e

    async def suggest_commands(
        self, intent: str, context: str | None = None
    ) -> AIResponse:
        """Suggest commands based on user intent."""

        cache_key = self._create_cache_key("suggest", intent, context or "")

        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response

        await self._rate_limit()

        session_context = self.context_manager.context_window.session
        recent_commands = self.context_manager.get_relevant_context(max_tokens=800)

        prompt = PromptTemplate.command_suggestion_prompt(
            intent=intent,
            session_context=session_context,
            recent_commands=recent_commands,
        )

        async with self.request_semaphore:
            try:
                response = await self.ollama_client.generate(prompt)
                self._cache_response(cache_key, response)
                self.metrics["requests_processed"] += 1

                await self._trigger_callbacks(
                    "commands_suggested", {"intent": intent, "response": response}
                )

                return response

            except Exception as e:
                self.metrics["requests_failed"] += 1
                raise e

    def register_callback(self, event: str, callback: Callable):
        """Register callback for specific events."""
        self.callbacks[event].append(callback)

    def get_metrics(self) -> dict[str, Any]:
        """Get current performance metrics."""
        return {
            **self.metrics,
            "cache_stats": self.cache_stats,
            "active_requests": len(self.active_requests),
            "cache_size": len(self.response_cache),
        }

    def clear_cache(self):
        """Clear response cache."""
        self.response_cache.clear()
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}

    async def _process_analysis_requests(self):
        """Background task to process analysis requests from context manager."""
        while self.is_running:
            try:
                request = await self.context_manager.get_next_analysis_request()

                if request:
                    task = asyncio.create_task(self._handle_analysis_request(request))
                    self.active_requests[request.request_id] = task

                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"Error in analysis request processing: {e}")
                await asyncio.sleep(1)

    async def _handle_analysis_request(self, request: AIAnalysisRequest):
        """Handle a single analysis request."""
        try:
            response = None

            if request.trigger.trigger_type.value == "error":
                response = await self.analyze_command_error(
                    command=request.context.command,
                    error_output=request.context.error,
                    context=self.context_manager.get_context_summary(),
                )
            elif request.trigger.trigger_type.value == "dangerous":
                session_context = request.session_context
                prompt = PromptTemplate.dangerous_command_warning_prompt(
                    command=request.context.command, session_context=session_context
                )
                response = await self.ollama_client.generate(prompt)
            elif request.trigger.trigger_type.value == "pattern":
                response = await self.analyze_command_output(
                    command=request.context.command,
                    output=request.context.output,
                    context=self.context_manager.get_context_summary(),
                )

            if response:
                await self._trigger_callbacks(
                    "analysis_completed", {"request": request, "response": response}
                )

        except Exception as e:
            print(f"Error handling analysis request {request.request_id}: {e}")
            await self._trigger_callbacks(
                "analysis_failed", {"request": request, "error": str(e)}
            )

        finally:
            if request.request_id in self.active_requests:
                del self.active_requests[request.request_id]

            self.context_manager.complete_analysis_request(request.request_id)

    async def _cache_cleanup_loop(self):
        """Background task to clean up expired cache entries."""
        while self.is_running:
            try:
                current_time = time.time()
                expired_keys = []

                for key, cached_response in self.response_cache.items():
                    if current_time - cached_response.timestamp > cached_response.ttl:
                        expired_keys.append(key)

                for key in expired_keys:
                    del self.response_cache[key]
                    self.cache_stats["evictions"] += 1

                await asyncio.sleep(60)

            except Exception as e:
                print(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)

    async def _update_metrics_loop(self):
        """Background task to update performance metrics."""
        while self.is_running:
            try:
                total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
                if total_requests > 0:
                    self.metrics["cache_hit_rate"] = (
                        self.cache_stats["hits"] / total_requests
                    )

                self.metrics["active_requests"] = len(self.active_requests)

                await asyncio.sleep(10)

            except Exception as e:
                print(f"Error updating metrics: {e}")
                await asyncio.sleep(10)

    async def _rate_limit(self):
        """Apply rate limiting to requests."""
        async with self.rate_limiter:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            min_interval = 1.0 / self.request_rate_limit

            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)

            self.last_request_time = time.time()

    async def _trigger_callbacks(self, event: str, data: dict[str, Any]):
        """Trigger callbacks for specific events."""
        for callback in self.callbacks[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                print(f"Callback error for event '{event}': {e}")

    def _create_cache_key(self, request_type: str, *args) -> str:
        """Create cache key from request parameters."""
        content = f"{request_type}:" + ":".join(str(arg) for arg in args)
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> AIResponse | None:
        """Get cached response if available and not expired."""
        if cache_key not in self.response_cache:
            self.cache_stats["misses"] += 1
            return None

        cached = self.response_cache[cache_key]
        current_time = time.time()

        if current_time - cached.timestamp > cached.ttl:
            del self.response_cache[cache_key]
            self.cache_stats["evictions"] += 1
            self.cache_stats["misses"] += 1
            return None

        cached.hit_count += 1
        self.cache_stats["hits"] += 1
        return cached.response

    def _cache_response(self, cache_key: str, response: AIResponse):
        """Cache an AI response."""
        self.response_cache[cache_key] = CachedResponse(
            response=response, timestamp=time.time(), hit_count=0, ttl=self.cache_ttl
        )
