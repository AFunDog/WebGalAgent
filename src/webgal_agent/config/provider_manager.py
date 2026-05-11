"""供应商配置管理器。

从 configs/providers.yaml 读写各智能体的 LLM 供应商设置。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from webgal_agent.core.agent import AgentConfig


class ProviderConfig(BaseModel):
    """单个智能体的 LLM 供应商设置。"""

    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


# 已知供应商预设
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
    """管理各智能体的 LLM 供应商配置。

    配置持久化到 ``configs/providers.yaml``。
    """

    def __init__(self, config_path: str | Path = "configs/providers.yaml") -> None:
        self._path = Path(config_path)
        self._configs: dict[str, ProviderConfig] = {}
        self._default_config = ProviderConfig()
        self.load()

    def load(self) -> None:
        """从 YAML 文件加载供应商配置。"""
        if not self._path.exists():
            self._configs = {}
            return

        data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        if not data or not isinstance(data, dict):
            return

        # 提取默认配置
        defaults_data = data.pop("defaults", None)
        if defaults_data and isinstance(defaults_data, dict):
            self._default_config = ProviderConfig(**defaults_data)

        # 提取各智能体配置（跳过 YAML 锚点如 <<）
        for agent_name, cfg in data.items():
            if isinstance(cfg, dict):
                # 与默认配置合并，填充缺失字段
                merged = self._default_config.model_dump()
                merged.update({k: v for k, v in cfg.items() if k != "<<"})
                self._configs[agent_name] = ProviderConfig(**merged)

    def save(self) -> None:
        """将当前配置持久化到 YAML 文件。"""
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
        """获取智能体的供应商配置，未配置则回退到默认值。"""
        return self._configs.get(agent_name, self._default_config)

    def set(self, agent_name: str, config: ProviderConfig) -> None:
        """设置智能体的供应商配置并持久化。"""
        self._configs[agent_name] = config
        self.save()

    def get_defaults(self) -> ProviderConfig:
        """获取默认供应商配置。"""
        return self._default_config

    def set_defaults(self, config: ProviderConfig) -> None:
        """设置默认供应商配置并持久化。"""
        self._default_config = config
        self.save()

    def list_agent_names(self) -> list[str]:
        """列出所有已配置的智能体名称。"""
        return list(self._configs.keys())

    def list_all(self) -> dict[str, ProviderConfig]:
        """返回所有智能体供应商配置。"""
        return dict(self._configs)

    def to_agent_config(self, agent_name: str, description: str = "") -> AgentConfig:
        """将供应商配置转换为 AgentConfig 实例。"""
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
