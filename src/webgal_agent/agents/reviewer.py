"""Reviewer agent — quality assurance and feedback.

The Reviewer is responsible for:
- Evaluating the quality of outputs from other agents
- Providing structured feedback for improvement
- Checking consistency across story, visuals, and format
- Scoring outputs against quality thresholds
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class ReviewerAgent(Agent):
    """Agent that reviews and provides feedback on other agents' outputs."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        config = config or AgentConfig(
            name="reviewer",
            description="Quality assurance and feedback agent",
        )
        super().__init__(config)

    def system_prompt(self) -> str:
        return (
            "你是一个质量审核员（Reviewer）。"
            "你的职责是：\n"
            "1. 评估其他 Agent 输出的质量\n"
            "2. 检查逻辑一致性和完整性\n"
            "3. 验证输出是否满足要求\n"
            "4. 给出结构化的改进建议和评分\n\n"
            "评分范围 0.0~1.0，0.8 以上视为通过。"
        )

    async def run(self, message: Message) -> Message:
        # TODO: integrate with LLM for review and scoring
        return message.reply(
            content="[Reviewer] 已收到待审核内容，开始评估...",
            msg_type=MessageType.FEEDBACK,
        )
