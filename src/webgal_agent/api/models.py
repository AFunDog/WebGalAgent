"""API 请求/响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------- 知识库 ----------

class KnowledgeResponse(BaseModel):
    """API 返回的知识库条目。"""

    id: str
    category: str
    title: str
    tags: list[str]
    body: str
    source: str
    created_at: datetime
    updated_at: datetime


class AgentKnowledgeRequirementsResponse(BaseModel):
    """从 prompts.yaml 配置的各智能体知识库需求。"""

    agent: str
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


# ---------- 工作流 ----------

class AgentInfoResponse(BaseModel):
    """智能体状态信息。"""

    name: str
    description: str
    state: str
    provider: str = ""
    model: str = ""


class WorkflowInfoResponse(BaseModel):
    """工作流配置信息。"""

    name: str
    agents: list[AgentInfoResponse]
    type: str
    description: str = ""


# ---------- 任务 ----------

class CreateTaskRequest(BaseModel):
    """创建任务请求体。"""

    content: str


class TaskMessageResponse(BaseModel):
    """任务执行中的消息。"""

    id: str
    type: str
    sender: str
    receiver: str
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class TaskResponse(BaseModel):
    """任务执行状态和结果。"""

    id: str
    status: str
    workflow: str
    content: str
    title: str = ""
    messages: list[TaskMessageResponse]
    errors: list[str]
    created_at: datetime
