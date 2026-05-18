"""读取 prompts.yaml 的共享配置辅助。

当前多个模块都依赖 prompts.yaml 中的 system_prompt 与 knowledge 段。
这里统一 YAML 解析逻辑，减少重复 IO 和重复 schema 解释。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROMPTS_CONFIG_PATH = Path("src/configs/prompts.yaml")


def load_prompt_config(path: str | Path = PROMPTS_CONFIG_PATH) -> dict[str, Any]:
    """读取 prompts.yaml 并返回原始配置字典。"""
    prompts_path = Path(path)
    if not prompts_path.exists():
        return {}

    data = yaml.safe_load(prompts_path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def extract_system_prompts(config: dict[str, Any]) -> dict[str, str]:
    """从原始 prompts 配置中提取 system_prompt 映射。"""
    result: dict[str, str] = {}
    for key, value in config.items():
        if isinstance(value, dict) and "system_prompt" in value:
            result[key] = str(value["system_prompt"]).strip()
    return result


def extract_knowledge_requirements(config: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    """从原始 prompts 配置中提取知识库筛选配置。"""
    result: dict[str, dict[str, list[str]]] = {}
    for key, value in config.items():
        if not isinstance(value, dict) or "knowledge" not in value:
            continue
        knowledge_cfg = value["knowledge"]
        if not isinstance(knowledge_cfg, dict):
            continue
        result[key] = {
            "categories": list(knowledge_cfg.get("categories", [])),
            "tags": list(knowledge_cfg.get("tags", [])),
        }
    return result
