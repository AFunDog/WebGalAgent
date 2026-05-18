"""prompts.yaml 配置读取辅助的单元测试。"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from webgal_agent.config.prompt_config import (
    extract_knowledge_requirements,
    extract_system_prompts,
    load_prompt_config,
)


def _workspace_temp_dir() -> Path:
    path = Path("data/temp") / f"pytest_prompt_config_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_load_prompt_config_reads_yaml() -> None:
    temp_dir = _workspace_temp_dir()
    config_file = temp_dir / "prompts.yaml"
    config_file.write_text(
        """
outline_writer:
  system_prompt: |
    You are outline writer.
  knowledge:
    categories: [character, world]
    tags: [story]
""".strip(),
        encoding="utf-8",
    )

    try:
        data = load_prompt_config(config_file)
        assert "outline_writer" in data
        assert data["outline_writer"]["knowledge"]["categories"] == ["character", "world"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_load_prompt_config_returns_empty_for_missing_file() -> None:
    temp_dir = _workspace_temp_dir()
    try:
        missing = temp_dir / "missing.yaml"
        assert load_prompt_config(missing) == {}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_extract_system_prompts_and_knowledge_requirements() -> None:
    raw = {
        "outline_writer": {
            "system_prompt": "  outline prompt  ",
            "knowledge": {"categories": ["character"], "tags": ["story"]},
        },
        "script_writer": {
            "knowledge": {"categories": ["plot"], "tags": []},
        },
        "invalid": "ignored",
    }

    prompts = extract_system_prompts(raw)
    requirements = extract_knowledge_requirements(raw)

    assert prompts == {"outline_writer": "outline prompt"}
    assert requirements == {
        "outline_writer": {"categories": ["character"], "tags": ["story"]},
        "script_writer": {"categories": ["plot"], "tags": []},
    }
