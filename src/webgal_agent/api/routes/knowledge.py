"""Knowledge base API routes (read-only)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from webgal_agent.api.models import KnowledgeResponse
from webgal_agent.knowledge import FileKnowledgeStore, KnowledgeEntry

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _get_store() -> FileKnowledgeStore:
    """Lazily get the shared knowledge store instance."""
    from webgal_agent.api.app import get_knowledge_store

    return get_knowledge_store()


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
) -> list[KnowledgeResponse]:
    """List all knowledge entries, optionally filtered by category or keyword."""
    store = _get_store()
    if category or keyword:
        entries = store.query(category=category, keyword=keyword)
    else:
        entries = store.list_all()
    return [_entry_to_response(e) for e in entries]


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    """List all distinct categories."""
    store = _get_store()
    entries = store.list_all()
    return sorted({e.category for e in entries})


@router.get("/{entry_id}", response_model=KnowledgeResponse)
async def get_entry(entry_id: str) -> KnowledgeResponse:
    """Get a single knowledge entry by ID."""
    store = _get_store()
    entry = store.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _entry_to_response(entry)


@router.post("/reload", status_code=200)
async def reload_knowledge() -> dict[str, str]:
    """Reload knowledge entries from disk."""
    store = _get_store()
    store.reload()
    return {"status": "ok", "count": str(store.count())}
