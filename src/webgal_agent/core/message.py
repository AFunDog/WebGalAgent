"""智能体间通信的消息类型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """智能体间交换的消息类型。"""

    TASK = "task"
    RESULT = "result"
    FEEDBACK = "feedback"
    CONTROL = "control"
    ERROR = "error"


class Message(BaseModel):
    """工作流中智能体间交换的消息。

    消息是通信的基本单元，承载结构化内容、元数据和路由信息。
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: MessageType = MessageType.TASK
    sender: str
    receiver: str
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def reply(self, content: str, msg_type: MessageType = MessageType.RESULT) -> Message:
        """创建从接收方回复发送方的消息。"""
        return Message(
            type=msg_type,
            sender=self.receiver,
            receiver=self.sender,
            content=content,
            metadata=self.metadata,
        )
