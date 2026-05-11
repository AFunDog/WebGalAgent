"""工作流中智能体间共享的执行上下文。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class SharedContext(BaseModel):
    """工作流中所有智能体可访问的共享上下文。

    用于传递项目级数据（如故事大纲、角色定义），
    供每个智能体引用。
    """

    project_name: str = ""
    story_outline: str = ""
    characters: list[dict[str, Any]] = field(default_factory=list)
    assets: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def with_extra(self, key: str, value: Any) -> SharedContext:
        """返回带有新增 ``extra`` 条目的副本。"""
        new_extra = {**self.extra, key: value}
        return self.model_copy(update={"extra": new_extra})
