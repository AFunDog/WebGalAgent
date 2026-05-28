from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from pathlib import Path

from webgal_agent.config.provider_manager import ProviderConfig
from webgal_agent.tools.search_expression_motion import (
    LLMRerankError,
    SearchExpressionMotionTool,
    _extract_json_array,
    load_expression_motion_retriever_prompt,
)


def _make_temp_dir() -> Path:
    path = Path("data/temp") / f"pytest_search_expression_motion_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_search_expression_motion_uses_expression_motion_json_only(monkeypatch) -> None:
    temp_dir = _make_temp_dir()
    anon_knowledge_file = (
        temp_dir / "knowledge" / "characters" / "千早爱音" / "expression_motion.json"
    )
    soyo_knowledge_file = (
        temp_dir / "knowledge" / "characters" / "长崎素世" / "expression_motion.json"
    )
    anon_knowledge_file.parent.mkdir(parents=True)
    soyo_knowledge_file.parent.mkdir(parents=True)
    anon_knowledge_file.write_text(
        json.dumps(
            [
                {
                    "action": "anon/thinking02",
                    "description": "双臂交叉，短暂闭眼低头，表现出沉思和无奈。",
                },
                {
                    "action": "anon/smile01",
                    "description": "轻松自然地微笑，情绪温和放松。",
                },
                {
                    "action": "anon/angry01",
                    "description": "眉头紧锁，语气强硬，明显生气。",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    soyo_knowledge_file.write_text(
        json.dumps(
            [
                {
                    "action": "soyo/smile01",
                    "description": "温和微笑，神情柔和放松。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBGAL_KNOWLEDGE_DIR", str(temp_dir / "knowledge"))

    try:
        tool = SearchExpressionMotionTool(provider_config=None)
        result = asyncio.run(
            tool.execute(
                character_id="anon",
                query_text="她沉默了一会，低下头思考，语气里有些无奈。",
                top_k=2,
            )
        )

        assert result.success is True
        payload = json.loads(result.output)
        assert len(payload["candidates"]) == 2
        assert payload["candidates"][0]["action"] == "anon/thinking02"
        assert {item["action"] for item in payload["candidates"]} <= {
            "anon/thinking02",
            "anon/smile01",
            "anon/angry01",
            "soyo/smile01",
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_search_expression_motion_respects_allowed_actions(monkeypatch) -> None:
    temp_dir = _make_temp_dir()
    anon_knowledge_file = (
        temp_dir / "knowledge" / "characters" / "千早爱音" / "expression_motion.json"
    )
    soyo_knowledge_file = (
        temp_dir / "knowledge" / "characters" / "长崎素世" / "expression_motion.json"
    )
    anon_knowledge_file.parent.mkdir(parents=True)
    soyo_knowledge_file.parent.mkdir(parents=True)
    anon_knowledge_file.write_text(
        json.dumps(
            [
                {
                    "action": "anon/thinking02",
                    "description": "双臂交叉，短暂闭眼低头，表现出沉思和无奈。",
                },
                {
                    "action": "anon/smile01",
                    "description": "轻松自然地微笑，情绪温和放松。",
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    soyo_knowledge_file.write_text(
        json.dumps(
            [
                {
                    "action": "soyo/smile01",
                    "description": "温和微笑，神情柔和放松。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBGAL_KNOWLEDGE_DIR", str(temp_dir / "knowledge"))

    try:
        tool = SearchExpressionMotionTool(provider_config=None)
        result = asyncio.run(
            tool.execute(
                character_id="anon",
                query_text="她轻轻笑了一下，气氛缓和下来。",
                top_k=2,
                allowed_actions=["soyo/smile01"],
            )
        )

        assert result.success is True
        payload = json.loads(result.output)
        assert [item["action"] for item in payload["candidates"]] == ["soyo/smile01"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_load_expression_motion_retriever_prompt_reads_from_prompts_yaml() -> None:
    temp_dir = _make_temp_dir()
    prompts_path = temp_dir / "prompts.yaml"
    prompts_path.write_text(
        """
expression_motion_retriever:
  system_prompt: |
    这是检索重排提示词
""".strip(),
        encoding="utf-8",
    )

    try:
        assert load_expression_motion_retriever_prompt(prompts_path) == "这是检索重排提示词"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_search_expression_motion_returns_llm_raw_output_on_fallback(monkeypatch) -> None:
    temp_dir = _make_temp_dir()
    knowledge_file = (
        temp_dir / "knowledge" / "characters" / "千早爱音" / "expression_motion.json"
    )
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text(
        json.dumps(
            [
                {
                    "action": "anon/thinking02",
                    "description": "双臂交叉，短暂闭眼低头，表现出沉思和无奈。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBGAL_KNOWLEDGE_DIR", str(temp_dir / "knowledge"))

    async def _raise_rerank_error(**kwargs):
        raise LLMRerankError("重排模型未返回有效候选", raw_output="not json at all")

    try:
        tool = SearchExpressionMotionTool(
            provider_config=ProviderConfig(
                provider="ollama",
                model="qwen3:4b",
                base_url="http://localhost:11434/v1",
                api_key="ollama",
            )
        )
        monkeypatch.setattr(tool, "_rerank_with_llm", _raise_rerank_error)
        result = asyncio.run(
            tool.execute(
                character_id="anon",
                query_text="她低头沉思。",
                top_k=1,
            )
        )

        assert result.success is True
        payload = json.loads(result.output)
        assert payload["candidates"][0]["action"] == "anon/thinking02"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_search_expression_motion_accepts_empty_llm_result(monkeypatch) -> None:
    temp_dir = _make_temp_dir()
    knowledge_file = (
        temp_dir / "knowledge" / "characters" / "千早爱音" / "expression_motion.json"
    )
    knowledge_file.parent.mkdir(parents=True)
    knowledge_file.write_text(
        json.dumps(
            [
                {
                    "action": "anon/thinking02",
                    "description": "双臂交叉，短暂闭眼低头，表现出沉思和无奈。",
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("WEBGAL_KNOWLEDGE_DIR", str(temp_dir / "knowledge"))

    async def _return_empty_candidates(**kwargs):
        return []

    try:
        tool = SearchExpressionMotionTool(
            provider_config=ProviderConfig(
                provider="deepseek",
                model="deepseek-v4-flash",
                base_url="https://api.deepseek.com",
                api_key="test-key",
            )
        )
        monkeypatch.setattr(tool, "_rerank_with_llm", _return_empty_candidates)
        result = asyncio.run(
            tool.execute(
                character_id="anon",
                query_text="她低头沉思。",
                top_k=1,
            )
        )

        assert result.success is True
        payload = json.loads(result.output)
        assert payload["candidates"] == []
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_extract_json_array_recovers_array_from_verbose_text() -> None:
    text = (
        "我先分析一下候选。\n"
        "最终结果如下：\n"
        '[{"action":"anon/thinking02","score":0.96,"reason":"最符合沉思和无奈。"}]'
    )

    parsed = _extract_json_array(text)

    assert parsed == [
        {
            "action": "anon/thinking02",
            "score": 0.96,
            "reason": "最符合沉思和无奈。",
        }
    ]


def test_search_expression_motion_sends_all_candidates_to_llm(monkeypatch) -> None:
    temp_dir = _make_temp_dir()
    knowledge_file = (
        temp_dir / "knowledge" / "characters" / "千早爱音" / "expression_motion.json"
    )
    knowledge_file.parent.mkdir(parents=True)
    entries = [
        {"action": f"anon/test{i:02d}", "description": f"这是第 {i} 个完整描述。" * 10}
        for i in range(1, 6)
    ]
    knowledge_file.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("WEBGAL_KNOWLEDGE_DIR", str(temp_dir / "knowledge"))
    captured: dict[str, object] = {}

    async def _capture_rerank(**kwargs):
        captured.update(kwargs)
        return []

    try:
        tool = SearchExpressionMotionTool(
            provider_config=ProviderConfig(
                provider="deepseek",
                model="deepseek-v4-flash",
                base_url="https://api.deepseek.com",
                api_key="test-key",
            )
        )
        monkeypatch.setattr(tool, "_rerank_with_llm", _capture_rerank)
        result = asyncio.run(
            tool.execute(
                character_id="anon",
                query_text="测试场景",
                top_k=3,
            )
        )

        assert result.success is True
        assert len(captured["shortlist"]) == 5
        assert all(
            len(str(item["description"])) == len(entries[idx]["description"])
            for idx, item in enumerate(captured["shortlist"])
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
