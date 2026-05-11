"""Execution context shared across agents in a workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel


class SharedContext(BaseModel):
    """Shared context accessible by all agents in a workflow.

    Use this to pass project-level data (e.g., story outline,
    character definitions) that every agent needs to reference.
    """

    project_name: str = ""
    story_outline: str = ""
    characters: list[dict[str, Any]] = field(default_factory=list)
    assets: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def with_extra(self, key: str, value: Any) -> SharedContext:
        """Return a copy with an additional entry in ``extra``."""
        new_extra = {**self.extra, key: value}
        return self.model_copy(update={"extra": new_extra})
