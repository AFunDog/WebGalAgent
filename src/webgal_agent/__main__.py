"""CLI entry point for starting the web UI server."""

from __future__ import annotations

import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="WebGalAgent Web UI Server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument(
        "--knowledge-dir",
        default="data/knowledge",
        help="Path to knowledge base directory (default: data/knowledge)",
    )
    args = parser.parse_args()

    uvicorn.run(
        "webgal_agent.api.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
