"""知识库存储抽象。"""

from __future__ import annotations

import abc
import re
from pathlib import Path

import yaml

from webgal_agent.knowledge.models import KnowledgeCategory, KnowledgeEntry


class KnowledgeStore(abc.ABC):
    """知识存储的抽象基类。

    提供 CRUD 和查询操作，供智能体在运行时
    查找参考信息（角色、设定等）。
    """

    @abc.abstractmethod
    def add(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        """添加新条目到存储。"""

    @abc.abstractmethod
    def get(self, entry_id: str) -> KnowledgeEntry | None:
        """根据 ID 检索条目。"""

    @abc.abstractmethod
    def update(self, entry_id: str, entry: KnowledgeEntry) -> KnowledgeEntry | None:
        """更新已有条目。未找到则返回 ``None``。"""

    @abc.abstractmethod
    def delete(self, entry_id: str) -> bool:
        """删除条目。存在则返回 ``True``。"""

    @abc.abstractmethod
    def query(
        self,
        category: str | None = None,
        tags: list[str] | None = None,
        keyword: str | None = None,
    ) -> list[KnowledgeEntry]:
        """按类别、标签或标题/正文关键词查询条目。"""

    @abc.abstractmethod
    def list_all(self) -> list[KnowledgeEntry]:
        """返回存储中的所有条目。"""

    @abc.abstractmethod
    def count(self) -> int:
        """返回条目总数。"""


class FileKnowledgeStore(KnowledgeStore):
    """从带 YAML frontmatter 的 Markdown 文件加载知识条目的存储。

    每个 ``.md`` 文件代表一条知识条目。YAML frontmatter
    提供结构化元数据（类别、标签、标题），Markdown 正文
    保存自由格式内容。

    文件结构示例::

        data/knowledge/
        ├── characters/
        │   ├── alice.md
        │   └── bob.md
        └── settings/
            ├── world.md
            └── main-scene.md

    ``alice.md`` 示例::

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
        self._entries: dict[str, KnowledgeEntry] = {}
        self._data_dir = Path(data_dir)
        self._load_all()

    def _load_all(self) -> None:
        """递归加载数据目录中的所有 Markdown 文件。"""
        if not self._data_dir.exists():
            return

        for path in sorted(self._data_dir.rglob("*.md")):
            self._load_file(path)

    def _load_file(self, path: Path) -> None:
        """加载单个带 YAML frontmatter 的 Markdown 文件。"""
        text = path.read_text(encoding="utf-8")
        match = self._FRONTMATTER_RE.match(text)

        if match:
            meta = yaml.safe_load(match.group(1)) or {}
            body = match.group(2)
        else:
            meta = {}
            body = text

        # 从 frontmatter 或首个标题推导标题
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

    def reload(self) -> None:
        """清空并从磁盘重新加载所有文件。"""
        self._entries.clear()
        self._load_all()
