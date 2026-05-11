"""Task manager for tracking workflow executions."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from webgal_agent.agents import ArtistAgent, DirectorAgent, ReviewerAgent, WriterAgent
from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.workflow import WorkflowResult
from webgal_agent.workflows.debate import DebateWorkflow
from webgal_agent.workflows.sequential import SequentialWorkflow


class TaskInfo:
    """Tracks a single workflow execution."""

    def __init__(self, task_id: str, workflow_name: str, content: str) -> None:
        self.id = task_id
        self.workflow_name = workflow_name
        self.content = content
        self.status: str = "pending"
        self.messages: list[Message] = []
        self.errors: list[str] = []
        self.created_at = datetime.utcnow()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "status": self.status,
            "workflow": self.workflow_name,
            "content": self.content,
            "messages": [
                {
                    "id": m.id,
                    "type": m.type.value,
                    "sender": m.sender,
                    "receiver": m.receiver,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in self.messages
            ],
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
        }


class TaskManager:
    """Manages workflow executions and their lifecycle."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._workflow_registry: dict[str, type[SequentialWorkflow | DebateWorkflow]] = {
            "sequential": SequentialWorkflow,
            "debate": DebateWorkflow,
        }

    @property
    def workflow_types(self) -> list[str]:
        return list(self._workflow_registry.keys())

    def _build_agents(self) -> dict[str, Agent]:
        return {
            "director": DirectorAgent(),
            "writer": WriterAgent(),
            "artist": ArtistAgent(),
            "reviewer": ReviewerAgent(),
        }

    def _build_workflow(self, workflow_name: str, agents: dict[str, Agent]) -> SequentialWorkflow | DebateWorkflow:
        cls = self._workflow_registry.get(workflow_name)
        if cls is None:
            raise ValueError(f"Unknown workflow type: {workflow_name}")

        if cls is SequentialWorkflow:
            return cls(agents=agents, order=["director", "writer", "artist", "reviewer"])
        if cls is DebateWorkflow:
            return cls(agents=agents, creator="writer", reviewer="reviewer", max_iterations=3)
        raise ValueError(f"Unhandled workflow type: {workflow_name}")

    async def start_task(self, content: str, workflow_name: str = "sequential") -> TaskInfo:
        """Create and start a new task."""
        task_id = uuid.uuid4().hex[:12]
        task = TaskInfo(task_id=task_id, workflow_name=workflow_name, content=content)
        self._tasks[task_id] = task

        agents = self._build_agents()
        workflow = self._build_workflow(workflow_name, agents)

        initial = Message(
            type=MessageType.TASK,
            sender="user",
            receiver="director",
            content=content,
        )

        task.status = "running"

        try:
            result: WorkflowResult = await workflow.execute(initial)
            task.messages = result.messages
            task.errors = result.errors
            task.status = "completed" if result.success else "failed"
        except Exception as exc:
            task.errors.append(str(exc))
            task.status = "failed"

        return task

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskInfo]:
        return list(self._tasks.values())

    def get_workflow_info(self, workflow_name: str) -> dict[str, object] | None:
        """Return static info about a workflow type."""
        if workflow_name not in self._workflow_registry:
            return None

        agents = self._build_agents()
        agent_list = [
            {"name": a.name, "description": a.description, "state": a.state.value}
            for a in agents.values()
        ]

        if workflow_name == "sequential":
            order = ["director", "writer", "artist", "reviewer"]
            return {
                "name": "sequential",
                "type": "SequentialWorkflow",
                "description": "顺序流水线：智能体按固定顺序依次执行",
                "agents": agent_list,
                "order": order,
            }
        if workflow_name == "debate":
            return {
                "name": "debate",
                "type": "DebateWorkflow",
                "description": "辩论迭代：创作者与审核员交替执行直到达到质量阈值",
                "agents": agent_list,
                "creator": "writer",
                "reviewer": "reviewer",
            }
        return None
