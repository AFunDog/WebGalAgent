"""基于 rich 的日志配置。"""

from __future__ import annotations

import logging

from rich.logging import RichHandler


def setup_logging(level: int = logging.INFO) -> None:
    """配置应用级 rich 日志输出。"""
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def get_logger(name: str) -> logging.Logger:
    """获取具名日志器实例。"""
    return logging.getLogger(name)
