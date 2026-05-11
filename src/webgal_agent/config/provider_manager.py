"""Provider configuration manager.

Reads and writes per-agent LLM provider settings from configs/providers.yaml.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from webgal_agent.core.agent import AgentConfig


class ProviderConfig(BaseModel):
    """LLM provider settings for a single agent."""

    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


# Well-known provider presets
PROVIDER_PRESETS: dict[str, dict[str, str]] = {
    "openai": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
    },
    "deepseek": {
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
    },
    "azure_openai": {
        "provider": "azure_openai",
        "base_url": "https://{resource}.openai.azure.com/openai/deployments/{deployment}",
    },
    "anthropic": {
        "provider": "anthropic",
        "base_url": "https://api.anthropic.com/v1",
    },
    "ollama": {
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
    },
    "custom": {
        "provider": "custom",
        "base_url": "",
    },
}


class ProviderConfigManager:
    """Manages per-agent LLM provider configurations.

    Configs are persisted to ``configs/providers.yaml``.
    """

    def __init__(self, config_path: str | Path = "configs/providers.yaml") -> None:
        self._path = Path(config_path)
        self._configs: dict[str, ProviderConfig] = {}
        self._default_config = ProviderConfig()
        self.load()

    def load(self) -> None:
        """Load provider configs from YAML file."""
        if not self._path.exists():
            self._configs = {}
            return

        data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        if not data or not isinstance(data, dict):
            return

        # Extract defaults
        defaults_data = data.pop("defaults", None)
        if defaults_data and isinstance(defaults_data, dict):
            self._default_config = ProviderConfig(**defaults_data)

        # Extract per-agent configs (skip YAML anchors like <<)
        for agent_name, cfg in data.items():
            if isinstance(cfg, dict):
                # Merge with defaults for missing fields
                merged = self._default_config.model_dump()
                merged.update({k: v for k, v in cfg.items() if k != "<<"})
                self._configs[agent_name] = ProviderConfig(**merged)

    def save(self) -> None:
        """Persist current configs to YAML file."""
        data: dict[str, object] = {
            "defaults": self._default_config.model_dump(),
        }
        for name, cfg in self._configs.items():
            data[name] = cfg.model_dump()

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def get(self, agent_name: str) -> ProviderConfig:
        """Get provider config for an agent, falling back to defaults."""
        return self._configs.get(agent_name, self._default_config)

    def set(self, agent_name: str, config: ProviderConfig) -> None:
        """Set provider config for an agent and persist."""
        self._configs[agent_name] = config
        self.save()

    def get_defaults(self) -> ProviderConfig:
        """Get the default provider config."""
        return self._default_config

    def set_defaults(self, config: ProviderConfig) -> None:
        """Set the default provider config and persist."""
        self._default_config = config
        self.save()

    def list_agent_names(self) -> list[str]:
        """List all configured agent names."""
        return list(self._configs.keys())

    def list_all(self) -> dict[str, ProviderConfig]:
        """Return all agent provider configs."""
        return dict(self._configs)

    def to_agent_config(self, agent_name: str, description: str = "") -> AgentConfig:
        """Convert a provider config into an AgentConfig instance."""
        pc = self.get(agent_name)
        return AgentConfig(
            name=agent_name,
            description=description,
            provider=pc.provider,
            model=pc.model,
            base_url=pc.base_url,
            api_key=pc.api_key,
            temperature=pc.temperature,
            max_tokens=pc.max_tokens,
        )
