#!/usr/bin/env python3
"""一键构建前端并启动后端服务。"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "src" / "frontend"

# 当前管理的子进程
_children: list[subprocess.Popen[bytes]] = []


def find_npm() -> str:
    """查找 npm 可执行文件。"""
    npm = shutil.which("npm")
    if npm:
        return npm
    for candidate in [
        os.path.expandvars(r"%APPDATA%\npm\npm.cmd"),
        os.path.expandvars(r"%PROGRAMFILES%\nodejs\npm.cmd"),
    ]:
        if Path(candidate).exists():
            return candidate
    print("错误: 未找到 npm，请先安装 Node.js", file=sys.stderr)
    sys.exit(1)


def build_frontend() -> None:
    """安装前端依赖并执行生产构建。"""
    npm = find_npm()
    print("=== 构建前端 ===")
    if not (FRONTEND_DIR / "node_modules").exists():
        print("[1/2] 安装依赖...")
        subprocess.run([npm, "install", "--prefix", str(FRONTEND_DIR)], check=True)
    else:
        print("[1/2] 依赖已存在，跳过安装")
    print("[2/2] 执行构建...")
    subprocess.run([npm, "run", "build", "--prefix", str(FRONTEND_DIR)], check=True)
    print("=== 前端构建完成 ===\n")


def _cleanup() -> None:
    """终止所有子进程。"""
    for p in _children:
        if p.poll() is None:
            p.terminate()
    for p in _children:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def _forward_signal(_signum: int, _frame: object) -> None:
    _cleanup()
    sys.exit(0)


def start_dev(backend_host: str, backend_port: int, frontend_port: int) -> None:
    """开发模式：同时启动 Vite（前端 HMR）和 uvicorn（后端热重载）。"""
    npm = find_npm()

    if not (FRONTEND_DIR / "node_modules").exists():
        print("=== 安装前端依赖 ===")
        subprocess.run([npm, "install", "--prefix", str(FRONTEND_DIR)], check=True)

    backend_env = {
        **os.environ,
        "WEBGAL_KNOWLEDGE_DIR": "data/knowledge",
        "WEBGAL_PROVIDERS_PATH": "src/configs/providers.yaml",
        "WEBGAL_BACKEND_HOST": backend_host,
        "WEBGAL_BACKEND_PORT": str(backend_port),
        "WEBGAL_FRONTEND_PORT": str(frontend_port),
    }

    print("=== 启动开发模式 ===")
    print(f"  后端: http://{backend_host}:{backend_port} (uvicorn --reload)")
    print(f"  前端: http://localhost:{frontend_port} (Vite HMR → 代理到后端)")
    print("  按 Ctrl+C 停止所有服务\n")

    backend = subprocess.Popen(
        [
            sys.executable, "-m", "webgal_agent",
            "--host", backend_host,
            "--port", str(backend_port),
            "--reload",
        ],
        env=backend_env,
    )
    _children.append(backend)

    frontend = subprocess.Popen(
        [npm, "run", "dev", "--prefix", str(FRONTEND_DIR)],
        env=backend_env,
    )
    _children.append(frontend)

    signal.signal(signal.SIGINT, _forward_signal)
    signal.signal(signal.SIGTERM, _forward_signal)

    # 等待任一子进程退出
    try:
        while True:
            for p in _children:
                code = p.poll()
                if code is not None:
                    print(f"\n子进程退出 (code={code})，正在关闭所有服务...")
                    _cleanup()
                    sys.exit(code)
    except KeyboardInterrupt:
        print("\n正在停止所有服务...")
        _cleanup()
        print("服务已停止")


def start_backend(host: str, port: int, reload: bool) -> None:
    """生产模式：启动后端服务。"""
    print(f"=== 启动后端服务 http://{host}:{port} ===")
    env = {
        **os.environ,
        "WEBGAL_KNOWLEDGE_DIR": "data/knowledge",
        "WEBGAL_PROVIDERS_PATH": "src/configs/providers.yaml",
    }
    cmd = [
        sys.executable, "-m", "webgal_agent",
        "--host", host,
        "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\n服务已停止")


def main() -> None:
    parser = argparse.ArgumentParser(description="一键启动 WebGalAgent 服务")
    parser.add_argument("--host", default="127.0.0.1", help="后端绑定主机 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="后端绑定端口 (默认: 8000)")
    parser.add_argument("--frontend-port", type=int, default=5173, help="前端 Vite 端口 (默认: 5173)")
    parser.add_argument("--dev", action="store_true", help="开发模式：前端 Vite HMR + 后端热重载")
    parser.add_argument("--skip-build", action="store_true", help="生产模式跳过前端构建")
    args = parser.parse_args()

    if args.dev:
        start_dev(args.host, args.port, args.frontend_port)
    else:
        if not args.skip_build:
            try:
                build_frontend()
            except subprocess.CalledProcessError as e:
                print(f"错误: 前端构建失败 (exit code {e.returncode})", file=sys.stderr)
                sys.exit(1)
        start_backend(args.host, args.port, reload=False)


if __name__ == "__main__":
    main()
