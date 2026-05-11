"""基于 rich 的日志配置。"""

from __future__ import annotations

import logging

from rich.logging import RichHandler

# 需要抑制的 uvicorn 访问日志 logger 名称
_NOISY_LOGGERS = ("uvicorn.access",)


def setup_logging(level: int = logging.INFO) -> None:
    """配置应用级 rich 日志输出，并抑制冗余的 HTTP 请求日志。"""
    # 先将 uvicorn.access 的 handler 清空，防止 basicConfig 又给它挂上
    for name in _NOISY_LOGGERS:
        noisy = logging.getLogger(name)
        noisy.handlers.clear()
        noisy.propagate = False
        noisy.setLevel(logging.WARNING)

    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def get_logger(name: str) -> logging.Logger:
    """获取具名日志器实例。"""
    return logging.getLogger(name)
