"""知识库模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class KnowledgeCategory(str, Enum):
    """预定义的知识类别。"""

    CHARACTER = "character"
    SETTING = "setting"
    PLOT = "plot"
    REFERENCE = "reference"
    CUSTOM = "custom"


class KnowledgeEntry(BaseModel):
    """知识库中的单条知识条目。

    每个条目代表一段独立信息（如角色档案、世界设定描述），
    供智能体在运行时查询。

    ``body`` 字段保存完整的 Markdown 内容，
    这是对人类编写和 LLM 消费都最自然的格式。
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: str = KnowledgeCategory.CUSTOM
    title: str = ""
    tags: list[str] = Field(default_factory=list)
    body: str = ""
    source: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        """更新 ``updated_at`` 时间戳。"""
        self.updated_at = datetime.utcnow()

    def full_content(self) -> str:
        """返回包含 frontmatter 的完整 Markdown 表示。

        适用于将条目直接传入 LLM 提示词。
        """
        return self.body
