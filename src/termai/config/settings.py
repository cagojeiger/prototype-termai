"""
Configuration management using pydantic-settings.

This module provides centralized configuration management for the Terminal AI Assistant.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Ollama Configuration
    ollama_host: str = Field(
        default="http://localhost:11434", description="Ollama server host URL"
    )
    ollama_model: str = Field(
        default="llama3.2:1b", description="Ollama model to use for AI analysis"
    )
    ollama_timeout: int = Field(default=30, description="Request timeout in seconds")

    # Application Settings
    app_log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    app_theme: str = Field(default="dark", description="UI theme (dark, light)")
    app_sidebar_width: int = Field(
        default=35, description="AI sidebar width percentage (0-100)"
    )

    # AI Settings
    ai_max_context_length: int = Field(
        default=20, description="Maximum number of commands to include in context"
    )
    ai_response_max_tokens: int = Field(
        default=500, description="Maximum tokens for AI response"
    )
    ai_temperature: float = Field(
        default=0.7, description="AI response temperature (0.0-1.0)"
    )
    ai_cache_enabled: bool = Field(
        default=True, description="Enable AI response caching"
    )
    ai_cache_ttl: int = Field(default=300, description="Cache TTL in seconds")

    # Terminal Settings
    terminal_shell: str | None = Field(
        default=None, description="Shell to use (defaults to $SHELL or /bin/bash)"
    )
    terminal_cols: int = Field(default=80, description="Default terminal columns")
    terminal_rows: int = Field(default=24, description="Default terminal rows")
    terminal_buffer_size: int = Field(
        default=10000, description="Maximum lines in output buffer"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow extra fields from environment
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Example usage
if __name__ == "__main__":
    settings = get_settings()
    print(f"Ollama Host: {settings.ollama_host}")
    print(f"Log Level: {settings.app_log_level}")
    print(f"AI Model: {settings.ollama_model}")
