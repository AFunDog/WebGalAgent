"""search_expression_motion 的命令行测试入口。"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path

from webgal_agent.config.provider_manager import ProviderConfigManager
from webgal_agent.tools.search_expression_motion import (
    DEFAULT_PROVIDER_SLOT,
    SearchExpressionMotionTool,
)
from webgal_agent.utils.logging import get_logger, setup_logging

logger = get_logger("webgal_agent.search_expression_motion_cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="测试 search_expression_motion 工具")
    parser.add_argument("--character-id", required=True, help="角色ID，例如 anon")
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--query-text", help="当前场景中与该角色相关的描写、对白或情绪描述")
    query_group.add_argument("--query-file", help="从文本文件读取 query_text")
    parser.add_argument("--top-k", type=int, default=3, help="返回候选数量，默认 3")
    parser.add_argument(
        "--allowed-action",
        action="append",
        default=[],
        help="限制候选 action，可重复传入，例如 --allowed-action anon/thinking02",
    )
    parser.add_argument(
        "--providers-path",
        default="src/configs/providers.yaml",
        help="providers.yaml 路径",
    )
    parser.add_argument(
        "--provider-slot",
        default=DEFAULT_PROVIDER_SLOT,
        help=f"本地重排模型槽位名，默认 {DEFAULT_PROVIDER_SLOT}",
    )
    parser.add_argument(
        "--prompts-path",
        default="src/configs/prompts.yaml",
        help="prompts.yaml 路径",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="禁用本地模型重排，只执行启发式检索",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="仅打印最终 JSON 结果，日志仍输出到 stderr",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="日志级别：DEBUG / INFO / WARNING / ERROR，默认 INFO",
    )
    return parser


def _load_query_text(args: argparse.Namespace) -> str:
    if args.query_text:
        return str(args.query_text).strip()
    return Path(str(args.query_file)).read_text(encoding="utf-8").strip()


def _resolve_provider_config(
    providers_path: str,
    provider_slot: str,
    no_llm: bool,
):
    if no_llm:
        logger.info("已禁用本地模型重排，仅使用启发式检索")
        return None

    provider_manager = ProviderConfigManager(providers_path)
    if provider_slot not in provider_manager.list_agent_names():
        logger.warning(
            "providers.yaml 未显式配置槽位 %s，回退到启发式检索",
            provider_slot,
        )
        return None

    config = provider_manager.get(provider_slot)
    logger.info(
        "启用本地模型重排: provider_slot=%s provider=%s model=%s base_url=%s",
        provider_slot,
        config.provider,
        config.model,
        config.base_url,
    )
    return config


async def _async_main(args: argparse.Namespace) -> int:
    query_text = _load_query_text(args)
    provider_config = _resolve_provider_config(
        providers_path=args.providers_path,
        provider_slot=args.provider_slot,
        no_llm=args.no_llm,
    )
    tool = SearchExpressionMotionTool(
        provider_config=provider_config,
        prompts_path=args.prompts_path,
    )

    logger.info(
        "开始调用工具: tool=%s character_id=%s top_k=%s allowed_actions=%s query_length=%s",
        tool.name,
        args.character_id,
        args.top_k,
        args.allowed_action or "ALL",
        len(query_text),
    )
    result = await tool.execute(
        character_id=args.character_id,
        query_text=query_text,
        top_k=args.top_k,
        allowed_actions=args.allowed_action,
    )
    logger.info(
        "工具调用完成: success=%s error=%s output_length=%s",
        result.success,
        result.error or "NONE",
        len(result.output),
    )

    if args.json_mode:
        print(result.output)
    else:
        print("=== Final Output ===")
        if result.output:
            try:
                payload = json.loads(result.output)
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            except json.JSONDecodeError:
                print(result.output)
        print(f"success={result.success}")
        print(f"error={result.error}")

    return 0 if result.success else 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    level = getattr(logging, str(args.log_level).upper(), logging.INFO)
    setup_logging(level=level)
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
