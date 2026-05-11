"""Application settings using pydantic-settings."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_")

    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


class AgentSettings(BaseSettings):
    """Per-agent configuration overrides."""

    model_config = SettingsConfigDict(env_prefix="AGENT_")

    director_model: str = "gpt-4o"
    writer_model: str = "gpt-4o"
    artist_model: str = "gpt-4o"
    reviewer_model: str = "gpt-4o"


class AppSettings(BaseSettings):
    """Top-level application settings.

    Reads from environment variables and optional ``.env`` file.
    Nested settings are loaded from their own prefixed env vars.
    """

    model_config = SettingsConfigDict(
        env_prefix="WEBGAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    debug: bool = False
    project_dir: Path = Path(".")
    llm: LLMSettings = Field(default_factory=LLMSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
