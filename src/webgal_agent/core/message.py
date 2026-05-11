"""Message types for inter-agent communication."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """Types of messages exchanged between agents."""

    TASK = "task"
    RESULT = "result"
    FEEDBACK = "feedback"
    CONTROL = "control"
    ERROR = "error"


class Message(BaseModel):
    """A message exchanged between agents in the workflow.

    Messages are the primary unit of communication. Each message carries
    structured content, metadata, and routing information.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: MessageType = MessageType.TASK
    sender: str
    receiver: str
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def with_type(self, msg_type: MessageType) -> Message:
        """Return a copy of this message with a different type."""
        return self.model_copy(update={"type": msg_type})

    def reply(self, content: str, msg_type: MessageType = MessageType.RESULT) -> Message:
        """Create a reply message from the receiver back to the sender."""
        return Message(
            type=msg_type,
            sender=self.receiver,
            receiver=self.sender,
            content=content,
            metadata=self.metadata,
        )
