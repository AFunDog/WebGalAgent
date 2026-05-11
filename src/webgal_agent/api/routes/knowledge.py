"""知识库 API 路由（只读）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from webgal_agent.api.models import AgentKnowledgeRequirementsResponse, KnowledgeResponse
from webgal_agent.knowledge import FileKnowledgeStore, KnowledgeEntry

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _get_store() -> FileKnowledgeStore:
    """延迟获取共享知识库实例。"""
    from webgal_agent.api.app import get_knowledge_store

    return get_knowledge_store()


def _get_task_manager():
    """延迟获取共享任务管理器实例。"""
    from webgal_agent.api.app import get_task_manager

    return get_task_manager()


def _entry_to_response(entry: KnowledgeEntry) -> KnowledgeResponse:
    return KnowledgeResponse(
        id=entry.id,
        category=entry.category,
        title=entry.title,
        tags=entry.tags,
        body=entry.body,
        source=entry.source,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


@router.get("", response_model=list[KnowledgeResponse])
async def list_entries(
    category: str | None = None,
    keyword: str | None = None,
    tags: str | None = None,
) -> list[KnowledgeResponse]:
    """列出所有知识库条目，可按类别、关键词或标签筛选。

    ``tags`` 参数接受逗号分隔的标签列表，
    匹配**任一**标签的条目都会返回。
    """
    store = _get_store()
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        entries = store.query(category=category, keyword=keyword, tags=tag_list)
    elif category or keyword:
        entries = store.query(category=category, keyword=keyword)
    else:
        entries = store.list_all()
    return [_entry_to_response(e) for e in entries]


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    """列出所有不重复的类别。"""
    store = _get_store()
    entries = store.list_all()
    return sorted({e.category for e in entries})


@router.get("/tags", response_model=list[str])
async def list_tags() -> list[str]:
    """列出所有条目中不重复的标签。"""
    store = _get_store()
    entries = store.list_all()
    return sorted({t for e in entries for t in e.tags})


@router.get("/agent-requirements", response_model=list[AgentKnowledgeRequirementsResponse])
async def get_agent_requirements() -> list[AgentKnowledgeRequirementsResponse]:
    """获取 prompts.yaml 中配置的各智能体知识库需求。"""
    tm = _get_task_manager()
    requirements = tm._knowledge_requirements
    return [
        AgentKnowledgeRequirementsResponse(
            agent=name,
            categories=req.get("categories", []),
            tags=req.get("tags", []),
        )
        for name, req in requirements.items()
    ]


@router.get("/{entry_id}", response_model=KnowledgeResponse)
async def get_entry(entry_id: str) -> KnowledgeResponse:
    """根据 ID 获取单个知识库条目。"""
    store = _get_store()
    entry = store.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="条目未找到")
    return _entry_to_response(entry)


@router.post("/reload", status_code=200)
async def reload_knowledge() -> dict[str, str]:
    """从磁盘重新加载知识库条目。"""
    store = _get_store()
    store.reload()
    return {"status": "ok", "count": str(store.count())}
