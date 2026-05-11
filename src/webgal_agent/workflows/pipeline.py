"""Pipeline workflow: A → B → C sequential execution with context accumulation.

Each agent receives the full accumulated context (user input, knowledge base,
and all previous outputs), not just the previous step's output.
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.workflow import Workflow, WorkflowResult


class PipelineWorkflow(Workflow):
    """Execute agents in a fixed pipeline order with accumulated context.

    Unlike a simple sequential workflow where each agent only sees the
    previous agent's output, this pipeline ensures every agent receives:

    - The original user input
    - The knowledge base context
    - All preceding agents' outputs

    This matches the design:

    - A: user_input + knowledge → outline
    - B: user_input + outline + knowledge → script
    - C: user_input + script + knowledge → WebGal script
    """

    def __init__(
        self,
        agents: dict[str, Agent],
        order: list[str],
        user_input: str = "",
        knowledge_context: str = "",
    ) -> None:
        super().__init__(agents)
        self._order = order
        self._user_input = user_input
        self._knowledge_context = knowledge_context

    @property
    def order(self) -> list[str]:
        return list(self._order)

    async def execute(self, initial_message: Message) -> WorkflowResult:
        messages: list[Message] = []
        errors: list[str] = []
        accumulated_outputs: list[str] = []

        for agent_name in self._order:
            # Build context message with all accumulated info
            context_parts: list[str] = []

            if self._user_input:
                context_parts.append(f"【用户输入】\n{self._user_input}")

            if self._knowledge_context:
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
                errors.append(f"Agent '{agent_name}' failed: {exc}")
                break

        return WorkflowResult(
            success=len(errors) == 0,
            messages=messages,
            errors=errors,
            metadata={"steps": [name for name in self._order]},
        )
