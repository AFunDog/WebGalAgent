"""Knowledge base API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from webgal_agent.api.models import (
    KnowledgeCreateRequest,
    KnowledgeResponse,
    KnowledgeUpdateRequest,
)
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
    """List all knowledge entries, optionally filtered."""
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


@router.post("", response_model=KnowledgeResponse, status_code=201)
async def create_entry(req: KnowledgeCreateRequest) -> KnowledgeResponse:
    """Create a new knowledge entry."""
    store = _get_store()
    entry = KnowledgeEntry(
        category=req.category,
        title=req.title,
        tags=req.tags,
        body=req.body,
    )
    store.add(entry)
    return _entry_to_response(entry)


@router.put("/{entry_id}", response_model=KnowledgeResponse)
async def update_entry(entry_id: str, req: KnowledgeUpdateRequest) -> KnowledgeResponse:
    """Update an existing knowledge entry."""
    store = _get_store()
    existing = store.get(entry_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    updated = existing.model_copy(
        update={
            k: v
            for k, v in req.model_dump().items()
            if v is not None
        }
    )
    result = store.update(entry_id, updated)
    if result is None:
        raise HTTPException(status_code=500, detail="Update failed")
    return _entry_to_response(result)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str) -> None:
    """Delete a knowledge entry."""
    store = _get_store()
    if not store.delete(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found")


@router.post("/reload", status_code=200)
async def reload_knowledge() -> dict[str, str]:
    """Reload knowledge entries from disk."""
    store = _get_store()
    store.reload()
    return {"status": "ok", "count": str(store.count())}
