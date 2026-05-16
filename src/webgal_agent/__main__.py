"""CLI 入口：启动 Web UI 服务器。"""

from __future__ import annotations

import argparse
import asyncio
import sys

# Windows: 必须在 uvicorn 及 playwright 前设置 ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="WebGalAgent Web UI 服务器")
    parser.add_argument("--host", default="127.0.0.1", help="绑定主机 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="绑定端口 (默认: 8000)")
    parser.add_argument("--reload", action="store_true", help="启用自动重载")
    parser.add_argument(
        "--knowledge-dir",
        default="data/knowledge",
        help="知识库目录路径 (默认: data/knowledge)",
    )
    parser.add_argument(
        "--providers-path",
        default="src/configs/providers.yaml",
        help="供应商配置 YAML 路径 (默认: src/configs/providers.yaml)",
    )
    args = parser.parse_args()

    # 通过环境变量传递配置路径，以便工厂函数能读取
    import os
    os.environ["WEBGAL_KNOWLEDGE_DIR"] = args.knowledge_dir
    os.environ["WEBGAL_PROVIDERS_PATH"] = args.providers_path

    uvicorn.run(
        "webgal_agent.api.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
