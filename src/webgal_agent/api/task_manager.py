"""Task manager for tracking workflow executions."""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

import yaml

from webgal_agent.agents import OutlineWriterAgent, ScriptConverterAgent, ScriptWriterAgent
from webgal_agent.config.provider_manager import ProviderConfigManager
from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.workflow import WorkflowResult
from webgal_agent.knowledge import KnowledgeStore
from webgal_agent.workflows.pipeline import PipelineWorkflow

# Pipeline step order: A → B → C
PIPELINE_ORDER = ["outline_writer", "script_writer", "script_converter"]

# Agent descriptions
AGENT_DESCRIPTIONS: dict[str, str] = {
    "outline_writer": "接受用户输入和知识库，编写剧本大纲",
    "script_writer": "接受用户输入、剧本大纲和知识库，生成各章节剧本",
    "script_converter": "接受用户输入、剧本和知识库，转换为 WebGal 引擎脚本",
}


class TaskInfo:
    """Tracks a single workflow execution."""

    def __init__(self, task_id: str, content: str) -> None:
        self.id = task_id
        self.workflow_name = "pipeline"
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


def _load_prompts() -> dict[str, str]:
    """Load agent prompts from configs/prompts.yaml."""
    prompts_path = Path("configs/prompts.yaml")
    if not prompts_path.exists():
        return {}

    data = yaml.safe_load(prompts_path.read_text(encoding="utf-8"))
    if not data or not isinstance(data, dict):
        return {}

    result: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, dict) and "system_prompt" in value:
            result[key] = value["system_prompt"].strip()
    return result


class TaskManager:
    """Manages pipeline workflow executions."""

    def __init__(
        self,
        knowledge_store: KnowledgeStore | None = None,
        provider_manager: ProviderConfigManager | None = None,
    ) -> None:
        self._tasks: dict[str, TaskInfo] = {}
        self._knowledge_store = knowledge_store
        self._provider_manager = provider_manager
        self._prompts = _load_prompts()

    @property
    def workflow_types(self) -> list[str]:
        return ["pipeline"]

    def _build_agents(self) -> dict[str, Agent]:
        agents: dict[str, Agent] = {}
        for name in PIPELINE_ORDER:
            # Build AgentConfig from provider manager if available
            if self._provider_manager:
                config = self._provider_manager.to_agent_config(
                    name, AGENT_DESCRIPTIONS.get(name, "")
                )
            else:
                from webgal_agent.core.agent import AgentConfig
                config = AgentConfig(
                    name=name,
                    description=AGENT_DESCRIPTIONS.get(name, ""),
                )

            prompt = self._prompts.get(name, "")

            if name == "outline_writer":
                agents[name] = OutlineWriterAgent(config=config, system_prompt=prompt)
            elif name == "script_writer":
                agents[name] = ScriptWriterAgent(config=config, system_prompt=prompt)
            elif name == "script_converter":
                agents[name] = ScriptConverterAgent(config=config, system_prompt=prompt)

        return agents

    def _build_knowledge_context(self) -> str:
        """Format knowledge base entries as context text for agents."""
        if self._knowledge_store is None:
            return ""

        entries = self._knowledge_store.list_all()
        if not entries:
            return ""

        parts: list[str] = []
        for entry in entries:
            header = f"### {entry.title}"
            if entry.category:
                header += f" [{entry.category}]"
            parts.append(f"{header}\n{entry.body}")

        return "\n\n".join(parts)

    async def start_task(self, content: str) -> TaskInfo:
        """Create and start a new pipeline task."""
        task_id = uuid.uuid4().hex[:12]
        task = TaskInfo(task_id=task_id, content=content)
        self._tasks[task_id] = task

        agents = self._build_agents()
        knowledge_context = self._build_knowledge_context()

        workflow = PipelineWorkflow(
            agents=agents,
            order=PIPELINE_ORDER,
            user_input=content,
            knowledge_context=knowledge_context,
        )

        initial = Message(
            type=MessageType.TASK,
            sender="user",
            receiver="outline_writer",
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

    def get_workflow_info(self) -> dict[str, object]:
        """Return info about the pipeline workflow."""
        agents = self._build_agents()
        agent_list = [
            {
                "name": a.name,
                "description": a.description,
                "state": a.state.value,
                "provider": a._config.provider,
                "model": a._config.model,
            }
            for a in agents.values()
        ]
        return {
            "name": "pipeline",
            "type": "PipelineWorkflow",
            "description": "三阶段流水线：A(大纲) → B(剧本) → C(WebGal脚本)",
            "agents": agent_list,
            "order": PIPELINE_ORDER,
        }
