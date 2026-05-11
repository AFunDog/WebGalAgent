"""Knowledge base models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class KnowledgeCategory(str, Enum):
    """Predefined knowledge categories."""

    CHARACTER = "character"
    SETTING = "setting"
    PLOT = "plot"
    REFERENCE = "reference"
    CUSTOM = "custom"


class KnowledgeEntry(BaseModel):
    """A single knowledge entry in the knowledge base.

    Each entry represents a discrete piece of information (e.g., a character
    profile, a world-setting description) that agents can query at runtime.

    The ``body`` field holds the full Markdown content, which is the most
    natural format for both human authoring and LLM consumption.
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
        """Update the ``updated_at`` timestamp."""
        self.updated_at = datetime.utcnow()

    def full_content(self) -> str:
        """Return the full Markdown representation including frontmatter.

        Useful when feeding the entry directly into an LLM prompt.
        """
        return self.body
