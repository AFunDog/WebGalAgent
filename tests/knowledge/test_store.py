"""知识库存储的基础单元测试。"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from webgal_agent.knowledge.models import KnowledgeCategory
from webgal_agent.knowledge.store import FileKnowledgeStore


def _workspace_temp_dir() -> Path:
    path = Path("data/temp") / f"pytest_knowledge_store_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_file_knowledge_store_defaults_category_without_frontmatter() -> None:
    temp_dir = _workspace_temp_dir()
    file_path = temp_dir / "plain.md"
    file_path.write_text("# Plain Entry\n\nNo frontmatter here.", encoding="utf-8")

    try:
        store = FileKnowledgeStore(temp_dir)
        entries = store.list_all()
        assert len(entries) == 1
        assert entries[0].category == KnowledgeCategory.CUSTOM
        assert entries[0].title == "Plain Entry"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
