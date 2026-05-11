"""FastAPI application factory and lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from webgal_agent.api.routes import knowledge, task, workflow
from webgal_agent.knowledge import FileKnowledgeStore

if TYPE_CHECKING:
    from webgal_agent.api.task_manager import TaskManager

# Module-level singletons (initialized in lifespan)
_knowledge_store: FileKnowledgeStore | None = None
_task_manager: TaskManager | None = None

_STATIC_DIR = Path(__file__).parent / "static"


def get_knowledge_store() -> FileKnowledgeStore:
    if _knowledge_store is None:
        raise RuntimeError("Application not initialized")
    return _knowledge_store


def get_task_manager() -> TaskManager:
    if _task_manager is None:
        raise RuntimeError("Application not initialized")
    return _task_manager


def create_app(knowledge_dir: str | Path = "data/knowledge") -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        knowledge_dir: Path to the knowledge base directory.
    """
    from webgal_agent.api.task_manager import TaskManager

    _resolved_knowledge_dir = str(Path(knowledge_dir).resolve())

    app = FastAPI(
        title="WebGalAgent",
        description="多智能体协作工作流框架",
        version="0.1.0",
    )

    @app.on_event("startup")
    async def _startup() -> None:
        global _knowledge_store, _task_manager
        _knowledge_store = FileKnowledgeStore(_resolved_knowledge_dir)
        _task_manager = TaskManager()

    # Register API routes
    app.include_router(knowledge.router)
    app.include_router(workflow.router)
    app.include_router(task.router)

    # Serve static frontend files (must be last — catch-all mount)
    if _STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app
