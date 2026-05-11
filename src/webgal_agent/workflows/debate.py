"""Debate-style iterative workflow.

Agents take turns reviewing and improving each other's outputs
until a quality threshold is met or the maximum iteration count
is reached.
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.workflow import Workflow, WorkflowResult


class DebateWorkflow(Workflow):
    """Iterative review-and-refine workflow.

    The workflow alternates between a creator agent and a reviewer
    agent. The reviewer evaluates the creator's output and provides
    feedback. If the quality score is below the threshold, the
    creator revises. This continues until the threshold is met
    or ``max_iterations`` is exhausted.

    Example::

        workflow = DebateWorkflow(
            agents={"writer": writer, "reviewer": reviewer},
            creator="writer",
            reviewer="reviewer",
            max_iterations=3,
            threshold=0.8,
        )
    """

    def __init__(
        self,
        agents: dict[str, Agent],
        creator: str,
        reviewer: str,
        max_iterations: int = 3,
        threshold: float = 0.8,
    ) -> None:
        super().__init__(agents)
        self._creator = creator
        self._reviewer = reviewer
        self._max_iterations = max_iterations
        self._threshold = threshold

    async def execute(self, initial_message: Message) -> WorkflowResult:
        messages: list[Message] = []
        errors: list[str] = []
        current_msg = initial_message

        creator = self.get_agent(self._creator)
        reviewer = self.get_agent(self._reviewer)

        for iteration in range(1, self._max_iterations + 1):
            # Creator produces / revises
            try:
                current_msg = await creator.handle(current_msg)
                messages.append(current_msg)
            except Exception as exc:
                errors.append(f"Iteration {iteration}: creator failed: {exc}")
                break

            # Reviewer evaluates
            review_msg = current_msg.reply(
                content=current_msg.content,
                sender=current_msg.receiver,
                receiver=self._reviewer,
            )
            try:
                review_result = await reviewer.handle(review_msg)
                messages.append(review_result)
            except Exception as exc:
                errors.append(f"Iteration {iteration}: reviewer failed: {exc}")
                break

            # Check quality threshold from metadata
            score = float(review_result.metadata.get("score", 0.0))
            if score >= self._threshold:
                break

            # Prepare feedback for next iteration
            current_msg = Message(
                type=MessageType.FEEDBACK,
                sender=self._reviewer,
                receiver=self._creator,
                content=review_result.content,
                metadata={"iteration": iteration, "score": score},
            )

        return WorkflowResult(
            success=len(errors) == 0,
            messages=messages,
            errors=errors,
            metadata={"iterations": min(iteration, self._max_iterations)},
        )
