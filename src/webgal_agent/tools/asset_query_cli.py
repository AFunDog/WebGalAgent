"""query_assets 的命令行测试入口。"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from webgal_agent.tools.asset_query import AssetQueryTool
from webgal_agent.utils.logging import get_logger, setup_logging

logger = get_logger("webgal_agent.asset_query_cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="测试 query_assets 工具")
    parser.add_argument(
        "--asset-type",
        required=True,
        choices=["character", "background", "bgm", "effect", "voice"],
        help="素材类型：character / background / bgm / effect / voice",
    )
    parser.add_argument(
        "--assets-dir",
        default=None,
        help="可选。覆盖默认素材根目录，例如 data/assets",
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


async def _async_main(args: argparse.Namespace) -> int:
    tool = AssetQueryTool(assets_dir=args.assets_dir)
    logger.info("开始调用工具: tool=%s asset_type=%s", tool.name, args.asset_type)

    result = await tool.execute(asset_type=args.asset_type)
    logger.info(
        "工具调用完成: success=%s error=%s output_length=%s",
        result.success,
        result.error or "NONE",
        len(result.output),
    )

    if args.json_mode:
        if result.success:
            print(result.output)
        else:
            print(json.dumps({"success": False, "error": result.error}, ensure_ascii=False))
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
