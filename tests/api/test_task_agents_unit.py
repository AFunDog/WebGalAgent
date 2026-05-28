from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from webgal_agent.api.task_agents import build_agents


def _make_task_dir() -> Path:
    task_dir = Path("data/temp") / f"pytest_task_agents_{uuid.uuid4().hex[:8]}"
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def test_build_agents_registers_expression_motion_search_tool() -> None:
    task_dir = _make_task_dir()
    try:
        agents = build_agents(prompts={}, provider_manager=None, task_dir=task_dir)
        script_converter = agents["script_converter"]

        assert "search_expression_motion" in script_converter.tools
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)
