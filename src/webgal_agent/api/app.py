"""FastAPI 应用工厂与生命周期管理。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from webgal_agent.api.routes import assets, knowledge, provider, task, workflow
from webgal_agent.config.provider_manager import ProviderConfigManager
from webgal_agent.knowledge import FileKnowledgeStore

if TYPE_CHECKING:
    from webgal_agent.api.task_manager import TaskManager

# 模块级单例（在 lifespan 中初始化）
_knowledge_store: FileKnowledgeStore | None = None
_task_manager: TaskManager | None = None
_provider_manager: ProviderConfigManager | None = None

_STATIC_DIR = Path(__file__).parent / "static"


def get_knowledge_store() -> FileKnowledgeStore:
    if _knowledge_store is None:
        raise RuntimeError("Application not initialized")
    return _knowledge_store


def get_task_manager() -> TaskManager:
    if _task_manager is None:
        raise RuntimeError("Application not initialized")
    return _task_manager


def get_provider_manager() -> ProviderConfigManager:
    if _provider_manager is None:
        raise RuntimeError("Application not initialized")
    return _provider_manager


def create_app(
    knowledge_dir: str | Path | None = None,
    providers_path: str | Path | None = None,
) -> FastAPI:
    """创建并配置 FastAPI 应用。

    参数：
        knowledge_dir: 知识库目录路径。
            默认使用环境变量 ``WEBGAL_KNOWLEDGE_DIR`` 或 ``data/knowledge``。
        providers_path: 供应商配置 YAML 路径。
            默认使用环境变量 ``WEBGAL_PROVIDERS_PATH`` 或 ``src/configs/providers.yaml``。
    """
    import os

    from webgal_agent.api.task_manager import TaskManager
    from webgal_agent.utils.logging import setup_logging

    # 初始化日志（抑制 uvicorn 访问日志）
    setup_logging()

    _resolved_knowledge_dir = str(Path(
        knowledge_dir or os.getenv("WEBGAL_KNOWLEDGE_DIR", "data/knowledge"),
    ).resolve())
    _resolved_providers_path = str(Path(
        providers_path or os.getenv("WEBGAL_PROVIDERS_PATH", "src/configs/providers.yaml"),
    ).resolve())

    app = FastAPI(
        title="WebGalAgent",
        description="多智能体协作工作流框架",
        version="0.1.0",
    )

    @app.on_event("startup")
    async def _startup() -> None:
        global _knowledge_store, _task_manager, _provider_manager
        _knowledge_store = FileKnowledgeStore(_resolved_knowledge_dir)
        _provider_manager = ProviderConfigManager(_resolved_providers_path)
        _task_manager = TaskManager(
            knowledge_store=_knowledge_store,
            provider_manager=_provider_manager,
            task_dir=os.getenv("WEBGAL_TASK_DIR", "data/tasks"),
        )

    # 注册 API 路由
    app.include_router(assets.router)
    app.include_router(knowledge.router)
    app.include_router(provider.router)
    app.include_router(workflow.router)
    app.include_router(task.router)

    # 提供静态前端文件（必须放在最后 — 通配挂载）
    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app
