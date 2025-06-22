"""
Ollama Client for Terminal AI Assistant

This module provides HTTP client functionality for communicating with
the local Ollama LLM server for AI-powered terminal assistance.
"""

import json
import time
from dataclasses import dataclass

import httpx
from pydantic import BaseModel


@dataclass
class AIResponse:
    """Structured AI response with analysis and suggestions."""

    content: str
    suggestions: list[str]
    warnings: list[str]
    errors: list[str]
    confidence: float
    response_time: float


class OllamaRequest(BaseModel):
    """Request model for Ollama API calls."""

    model: str
    prompt: str
    stream: bool = False
    options: dict = {}


class OllamaClient:
    """HTTP client for communicating with local Ollama LLM server."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "llama3.2:1b",
        timeout: int = 30,
        max_tokens: int = 500,
    ):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

        self._available_models: list[str] | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """Get list of available models from Ollama server."""
        try:
            response = await self.client.get(f"{self.host}/api/tags")
            response.raise_for_status()

            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            self._available_models = models
            return models

        except Exception as e:
            raise ConnectionError(f"Failed to fetch models from Ollama: {e}") from e

    async def generate(
        self, prompt: str, model: str | None = None, stream: bool = False, **options
    ) -> AIResponse:
        """Generate AI response for the given prompt."""
        import time

        start_time = time.time()

        model = model or self.model

        if self._available_models is None:
            await self.list_models()

        if self._available_models and model not in self._available_models:
            raise ValueError(
                f"Model '{model}' not available. Available models: {self._available_models}"
            )

        request_data = OllamaRequest(
            model=model,
            prompt=prompt,
            stream=stream,
            options={
                "num_predict": self.max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                **options,
            },
        )

        try:
            response = await self.client.post(
                f"{self.host}/api/generate",
                json=request_data.model_dump(),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            if stream:
                return await self._handle_streaming_response(response, start_time)
            else:
                return await self._handle_single_response(response, start_time)

        except httpx.TimeoutException as e:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s") from e
        except httpx.HTTPStatusError as e:
            raise ConnectionError(
                f"Ollama API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error during Ollama request: {e}") from e

    async def _handle_single_response(
        self, response: httpx.Response, start_time: float
    ) -> AIResponse:
        """Handle non-streaming response from Ollama."""
        data = response.json()
        content = data.get("response", "")
        response_time = time.time() - start_time

        return self._parse_ai_response(content, response_time)

    async def _handle_streaming_response(
        self, response: httpx.Response, start_time: float
    ) -> AIResponse:
        """Handle streaming response from Ollama."""
        content_parts = []

        async for line in response.aiter_lines():
            if line.strip():
                try:
                    chunk = json.loads(line)
                    if "response" in chunk:
                        content_parts.append(chunk["response"])
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    continue

        content = "".join(content_parts)
        response_time = time.time() - start_time

        return self._parse_ai_response(content, response_time)

    def _parse_ai_response(self, content: str, response_time: float) -> AIResponse:
        """Parse AI response content into structured format."""
        suggestions = []
        warnings = []
        errors = []
        confidence = 0.8  # Default confidence

        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("SUGGESTION:") or line.startswith("💡"):
                suggestions.append(
                    line.replace("SUGGESTION:", "").replace("💡", "").strip()
                )
            elif line.startswith("WARNING:") or line.startswith("⚠️"):
                warnings.append(line.replace("WARNING:", "").replace("⚠️", "").strip())
            elif line.startswith("ERROR:") or line.startswith("❌"):
                errors.append(line.replace("ERROR:", "").replace("❌", "").strip())

        if errors:
            confidence = max(0.6, confidence - 0.1 * len(errors))
        if warnings:
            confidence = max(0.7, confidence - 0.05 * len(warnings))
        if suggestions:
            confidence = min(0.95, confidence + 0.05 * len(suggestions))

        return AIResponse(
            content=content,
            suggestions=suggestions,
            warnings=warnings,
            errors=errors,
            confidence=confidence,
            response_time=response_time,
        )

    async def analyze_command_error(
        self, command: str, error_output: str, context: str | None = None
    ) -> AIResponse:
        """Analyze command execution error and provide suggestions."""
        prompt = f"""You are a terminal AI assistant. A user executed a command that resulted in an error.

Command: {command}
Error Output: {error_output}
"""

        if context:
            prompt += f"Additional Context: {context}\n"

        prompt += """
Please analyze this error and provide:
1. A clear explanation of what went wrong
2. Specific suggestions to fix the issue (prefix with 'SUGGESTION:')
3. Any warnings about potential risks (prefix with 'WARNING:')
4. Alternative approaches if applicable

Keep your response concise and actionable. Focus on practical solutions.
"""

        return await self.generate(prompt)

    async def analyze_command_output(
        self, command: str, output: str, context: str | None = None
    ) -> AIResponse:
        """Analyze successful command output for insights and suggestions."""
        prompt = f"""You are a terminal AI assistant. A user executed a command successfully.

Command: {command}
Output: {output}
"""

        if context:
            prompt += f"Additional Context: {context}\n"

        prompt += """
Please analyze this command and output to provide:
1. Brief explanation of what the command accomplished
2. Useful insights or observations about the results
3. Related commands or next steps that might be helpful (prefix with 'SUGGESTION:')
4. Any potential issues or considerations (prefix with 'WARNING:')

Keep your response brief and focused on actionable insights.
"""

        return await self.generate(prompt)

    async def suggest_command(
        self, intent: str, context: str | None = None
    ) -> AIResponse:
        """Suggest commands based on user intent and context."""
        prompt = f"""You are a terminal AI assistant. A user wants to accomplish something.

User Intent: {intent}
"""

        if context:
            prompt += f"Current Context: {context}\n"

        prompt += """
Please suggest appropriate terminal commands to accomplish this goal:
1. Provide specific command suggestions (prefix with 'SUGGESTION:')
2. Explain what each command does
3. Include any important warnings or considerations (prefix with 'WARNING:')
4. Mention any prerequisites or setup needed

Focus on safe, commonly-used commands. Prioritize clarity and safety.
"""

        return await self.generate(prompt)


async def create_ollama_client(
    host: str = "http://localhost:11434", model: str = "llama3.2:1b"
) -> OllamaClient:
    """Create and initialize an Ollama client."""
    client = OllamaClient(host=host, model=model)

    if not await client.health_check():
        raise ConnectionError(f"Cannot connect to Ollama server at {host}")

    await client.list_models()
    return client
