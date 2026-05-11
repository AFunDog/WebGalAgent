"""Knowledge store abstractions."""

from __future__ import annotations

import abc
import re
from pathlib import Path

import yaml

from webgal_agent.knowledge.models import KnowledgeEntry


class KnowledgeStore(abc.ABC):
    """Abstract base class for knowledge storage.

    Provides CRUD and query operations that agents use to look up
    reference information (characters, settings, etc.) at runtime.
    """

    @abc.abstractmethod
    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """Add a new entry to the store."""

    @abc.abstractmethod
    def get(self, entry_id: str) -> KnowledgeEntry | None:
        """Retrieve an entry by its ID."""

    @abc.abstractmethod
    def update(self, entry_id: str, entry: KnowledgeEntry) -> KnowledgeEntry | None:
        """Update an existing entry. Returns ``None`` if not found."""

    @abc.abstractmethod
    def delete(self, entry_id: str) -> bool:
        """Delete an entry. Returns ``True`` if it existed."""

    @abc.abstractmethod
    def query(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        keyword: str | None = None,
    ) -> list[KnowledgeEntry]:
        """Query entries by category, tags, or keyword in title/body."""

    @abc.abstractmethod
    def list_all(self) -> list[KnowledgeEntry]:
        """Return all entries in the store."""

    @abc.abstractmethod
    def count(self) -> int:
        """Return the total number of entries."""


class InMemoryKnowledgeStore(KnowledgeStore):
    """Simple in-memory knowledge store backed by a dict."""

    def __init__(self) -> None:
        self._entries: dict[str, KnowledgeEntry] = {}

    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        self._entries[entry.id] = entry
        return entry

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        return self._entries.get(entry_id)

    def update(self, entry_id: str, entry: KnowledgeEntry) -> KnowledgeEntry | None:
        if entry_id not in self._entries:
            return None
        entry.touch()
        self._entries[entry_id] = entry
        return entry

    def delete(self, entry_id: str) -> bool:
        return self._entries.pop(entry_id, None) is not None

    def query(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        keyword: str | None = None,
    ) -> list[KnowledgeEntry]:
        results = list(self._entries.values())

        if category is not None:
            results = [e for e in results if e.category == category]

        if tags:
            tag_set = set(tags)
            results = [e for e in results if tag_set & set(e.tags)]

        if keyword is not None:
            kw = keyword.lower()
            results = [
                e for e in results if kw in e.title.lower() or kw in e.body.lower()
            ]

        return results

    def list_all(self) -> list[KnowledgeEntry]:
        return list(self._entries.values())

    def count(self) -> int:
        return len(self._entries)


class FileKnowledgeStore(InMemoryKnowledgeStore):
    """Knowledge store that loads entries from Markdown files with YAML frontmatter.

    Each ``.md`` file represents one knowledge entry. The YAML frontmatter
    provides structured metadata (category, tags, title), while the Markdown
    body holds the free-form content.

    Example file structure::

        data/knowledge/
        ├── characters/
        │   ├── alice.md
        │   └── bob.md
        └── settings/
            ├── world.md
            └── main-scene.md

    Example ``alice.md``::

        ---
        category: character
        tags: [protagonist, human]
        title: Alice
        ---

        # Alice

        ## 基本信息
        - 年龄：18
        - 性别：女

        ## 性格
        勇敢、善良、略带倔强
    """

    _FRONTMATTER_RE = re.compile(
        r"\A---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL
    )

    def __init__(self, data_dir: str | Path) -> None:
        super().__init__()
        self._data_dir = Path(data_dir)
        self._load_all()

    def _load_all(self) -> None:
        """Recursively load all Markdown files from the data directory."""
        if not self._data_dir.exists():
            return

        for path in sorted(self._data_dir.rglob("*.md")):
            self._load_file(path)

    def _load_file(self, path: Path) -> None:
        """Load a single Markdown file with YAML frontmatter."""
        text = path.read_text(encoding="utf-8")
        match = self._FRONTMATTER_RE.match(text)

        if match:
            meta = yaml.safe_load(match.group(1)) or {}
            body = match.group(2)
        else:
            meta = {}
            body = text

        # Derive title from frontmatter or first heading
        title = meta.get("title", "")
        if not title:
            heading_match = re.search(r"^#\s+(.+)", body, re.MULTILINE)
            title = heading_match.group(1).strip() if heading_match else path.stem

        entry = KnowledgeEntry(
            category=meta.get("category", KnowledgeCategory.CUSTOM if not meta else "custom"),
            title=title,
            tags=meta.get("tags", []),
            body=body.strip(),
            source=str(path.relative_to(self._data_dir)),
        )
        self.add(entry)

    def reload(self) -> None:
        """Clear and re-load all files from disk."""
        self._entries.clear()
        self._load_all()
