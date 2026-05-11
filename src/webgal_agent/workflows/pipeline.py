"""流水线工作流：A → B → C 顺序执行，带上下文累积。

每个智能体接收完整的累积上下文（用户输入、知识库和所有前序输出），
而不仅仅是上一步的输出。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.workflow import Workflow, WorkflowResult


class PipelineWorkflow(Workflow):
    """按固定顺序执行智能体，并累积上下文。

    与简单顺序工作流（每个智能体只看到上一步输出）不同，
    本流水线确保每个智能体接收：

    - 原始用户输入
    - 知识库上下文（按智能体筛选）
    - 所有前序智能体的输出

    对应设计：

    - A: 用户输入 + 知识库 → 大纲
    - B: 用户输入 + 大纲 + 知识库 → 剧本
    - C: 用户输入 + 剧本 + 知识库 → WebGal 脚本
    """

    def __init__(
        self,
        agents: dict[str, Agent],
        order: list[str],
        user_input: str = "",
        knowledge_context: str = "",
        knowledge_contexts: dict[str, str] | None = None,
    ) -> None:
        super().__init__(agents)
        self._order = order
        self._user_input = user_input
        # 各智能体独立的知识库上下文优先于全局上下文
        self._knowledge_contexts = knowledge_contexts or {}
        self._knowledge_context = knowledge_context

    @property
    def order(self) -> list[str]:
        return list(self._order)

    async def execute(self, initial_message: Message) -> WorkflowResult:
        messages: list[Message] = []
        errors: list[str] = []
        accumulated_outputs: list[str] = []

        for agent_name in self._order:
            # 构建包含所有累积信息的上下文消息
            context_parts: list[str] = []

            if self._user_input:
                context_parts.append(f"【用户输入】\n{self._user_input}")

            if self._knowledge_contexts:
                # 使用各智能体独立的知识库上下文
                agent_knowledge = self._knowledge_contexts.get(agent_name, "")
                if agent_knowledge:
                    context_parts.append(f"【知识库】\n{agent_knowledge}")
            elif self._knowledge_context:
                # 回退到全局知识库上下文
                context_parts.append(f"【知识库】\n{self._knowledge_context}")

            for idx, output in enumerate(accumulated_outputs):
                step_name = self._order[idx] if idx < len(self._order) else f"step_{idx}"
                context_parts.append(f"【{step_name} 的输出】\n{output}")

            context_content = "\n\n".join(context_parts) if context_parts else initial_message.content

            current_msg = Message(
                type=MessageType.TASK,
                sender="pipeline",
                receiver=agent_name,
                content=context_content,
                metadata={
                    "user_input": self._user_input,
                    "step": agent_name,
                },
            )

            try:
                agent = self.get_agent(agent_name)
                result = await agent.handle(current_msg)
                messages.append(result)
                accumulated_outputs.append(result.content)
            except Exception as exc:
                errors.append(f"智能体 '{agent_name}' 执行失败: {exc}")
                break

        return WorkflowResult(
            success=len(errors) == 0,
            messages=messages,
            errors=errors,
            metadata={"steps": [name for name in self._order]},
        )
