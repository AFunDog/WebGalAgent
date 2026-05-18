"""浏览器录制 CLI 入口。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Windows: 必须在 import playwright 前设置 ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# 确保 src 路径在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webgal_agent.browser.demo_cli import build_parser, run_cli
from webgal_agent.browser.demo_session import demo_navigate, demo_record


def main() -> None:
    """CLI 入口。"""
    run_cli(build_parser().parse_args())


if __name__ == "__main__":
    main()
