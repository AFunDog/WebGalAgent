from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from pathlib import Path

from webgal_agent.tools.read_model import ReadModelTool


def _make_temp_dir() -> Path:
    path = Path("data/temp") / f"pytest_read_model_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_read_model_includes_expression_motion_descriptions(monkeypatch) -> None:
    temp_dir = _make_temp_dir()
    figure_model = temp_dir / "figure" / "anon" / "casual-2023" / "model.json"
    knowledge_file = (
        temp_dir / "knowledge" / "characters" / "千早爱音" / "expression_motion.json"
    )
    figure_model.parent.mkdir(parents=True)
    knowledge_file.parent.mkdir(parents=True)
    figure_model.write_text(
        json.dumps(
            {
                "motions": {"smile01": {}, "idle01": {}},
                "expressions": [{"name": "smile01"}, {"name": "angry01"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    knowledge_file.write_text(
        json.dumps(
            [
                {
                    "action": "anon/smile01",
                    "description": "带着温和笑意微微歪头。",
                },
                {
                    "action": "soyo/smile01",
                    "description": "不应被读到。",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBGAL_KNOWLEDGE_DIR", str(temp_dir / "knowledge"))

    try:
        tool = ReadModelTool(figure_dir=temp_dir / "figure")
        result = asyncio.run(tool.execute(path="anon/casual-2023/model.json"))

        assert result.success is True
        payload = json.loads(result.output)
        assert payload["path"] == "anon/casual-2023/model.json"
        assert payload["motions"] == ["idle01", "smile01"]
        assert payload["expressions"] == ["angry01", "smile01"]
        assert payload["descriptions"] == {
            "anon/smile01": "带着温和笑意微微歪头。",
        }
        assert payload["description_source"] == "characters/千早爱音/expression_motion.json"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
