"""软链接管理 API 路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from webgal_agent.scene_link import SceneLinkManager

router = APIRouter(prefix="/scene-link", tags=["scene-link"])

# 模块级单例
_manager: SceneLinkManager | None = None


def get_manager() -> SceneLinkManager:
    if _manager is None:
        raise RuntimeError("SceneLinkManager not initialized")
    return _manager


def init_manager(
    result_base_dir: str | Path = "data/tasks",
    link_root: str | Path = r"D:\Data\WebGal",
) -> None:
    global _manager
    _manager = SceneLinkManager(
        result_base_dir=result_base_dir,
        default_link_root=link_root,
    )


class CreateLinkRequest(BaseModel):
    """创建软链接请求。"""

    task_id: str
    link_path: str | None = None
    force: bool = False


class LinkResponse(BaseModel):
    """软链接操作响应。"""

    success: bool
    message: str
    link_path: str | None = None
    target_path: str | None = None


class LinkStatusResponse(BaseModel):
    """软链接状态响应。"""

    path: str
    exists: bool
    is_symlink: bool
    target: str | None
    valid: bool


@router.post("/create", response_model=LinkResponse)
async def create_link(req: CreateLinkRequest) -> LinkResponse:
    """创建软链接。"""
    manager = get_manager()
    result = manager.create_link(
        task_id=req.task_id,
        link_path=req.link_path,
        force=req.force,
    )
    return LinkResponse(
        success=result.success,
        message=result.message,
        link_path=result.link_path,
        target_path=result.target_path,
    )


@router.post("/remove", response_model=LinkResponse)
async def remove_link(link_path: str | None = None) -> LinkResponse:
    """删除软链接。"""
    manager = get_manager()
    result = manager.remove_link(link_path=link_path)
    return LinkResponse(
        success=result.success,
        message=result.message,
        link_path=result.link_path,
        target_path=result.target_path,
    )


@router.get("/status", response_model=LinkStatusResponse)
async def get_status(link_path: str | None = None) -> LinkStatusResponse:
    """获取软链接状态。"""
    manager = get_manager()
    status = manager.get_link_status(link_path=link_path)
    return LinkStatusResponse(**status)


@router.get("/tasks", response_model=list[str])
async def list_tasks() -> list[str]:
    """列出所有可用的任务 ID。"""
    manager = get_manager()
    result_dir = manager.result_base_dir
    if not result_dir.exists():
        return []
    return [d.name for d in result_dir.iterdir() if d.is_dir()]
