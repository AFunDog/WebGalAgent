"""Sequential pipeline workflow.

Agents execute one after another in a defined order. The output of
each agent becomes the input of the next.
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message
from webgal_agent.core.workflow import Workflow, WorkflowResult


class SequentialWorkflow(Workflow):
    """Execute agents in a fixed sequential order.

    Example::

        workflow = SequentialWorkflow(
            agents={"a": agent_a, "b": agent_b},
            order=["a", "b"],
        )
        result = await workflow.execute(initial_message)
    """

    def __init__(
        self,
        agents: dict[str, Agent],
        order: list[str],
    ) -> None:
        super().__init__(agents)
        self._order = order

    @property
    def order(self) -> list[str]:
        return list(self._order)

    async def execute(self, initial_message: Message) -> WorkflowResult:
        messages: list[Message] = []
        errors: list[str] = []
        current_msg = initial_message

        for agent_name in self._order:
            try:
                agent = self.get_agent(agent_name)
                current_msg = await agent.handle(current_msg)
                messages.append(current_msg)
            except Exception as exc:
                errors.append(f"Agent '{agent_name}' failed: {exc}")
                break

        return WorkflowResult(
            success=len(errors) == 0,
            messages=messages,
            errors=errors,
        )
