from __future__ import annotations

import argparse
import json

from webgal_agent.tools.search_expression_motion_cli import _async_main, build_parser


def test_build_parser_accepts_character_id_and_query_text() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "--character-id",
            "anon",
            "--query-text",
            "她低头沉思。",
            "--top-k",
            "2",
            "--no-llm",
        ]
    )

    assert args.character_id == "anon"
    assert args.query_text == "她低头沉思。"
    assert args.top_k == 2
    assert args.no_llm is True


async def test_async_main_prints_final_output_without_llm(monkeypatch, capsys) -> None:
    class _StubTool:
        name = "search_expression_motion"

        async def execute(self, **kwargs):
            from webgal_agent.tools.base import ToolResult

            return ToolResult(
                success=True,
                output=json.dumps(
                    {
                        "character_id": kwargs["character_id"],
                        "backend": "heuristic",
                        "candidates": [{"action": "anon/thinking02"}],
                    },
                    ensure_ascii=False,
                ),
            )

    monkeypatch.setattr(
        "webgal_agent.tools.search_expression_motion_cli.SearchExpressionMotionTool",
        lambda provider_config=None, prompts_path="": _StubTool(),
    )

    args = argparse.Namespace(
        character_id="anon",
        query_text="她低头沉思。",
        query_file=None,
        top_k=3,
        providers_path="src/configs/providers.yaml",
        provider_slot="expression_motion_retriever",
        prompts_path="src/configs/prompts.yaml",
        no_llm=True,
        json_mode=False,
        log_level="INFO",
    )

    exit_code = await _async_main(args)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "=== Final Output ===" in captured.out
    assert '"backend": "heuristic"' in captured.out
    assert "success=True" in captured.out
