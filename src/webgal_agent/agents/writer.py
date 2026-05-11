"""Writer agent — content generation.

The Writer is responsible for:
- Generating structured content based on task assignments
- Adapting style and tone to requirements
- Producing drafts for review
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class WriterAgent(Agent):
    """Agent that generates content based on task assignments."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        config = config or AgentConfig(
            name="writer",
            description="Script and dialogue generation agent",
        )
        super().__init__(config)

    def system_prompt(self) -> str:
        return (
            "你是一个内容创作专家（Writer）。"
            "你的职责是：\n"
            "1. 根据导演的分解任务进行创作\n"
            "2. 按照要求生成结构化的内容\n"
            "3. 保持风格和逻辑的一致性\n"
            "4. 根据反馈迭代改进\n\n"
            "输出应清晰、结构化，便于后续处理。"
        )

    async def run(self, message: Message) -> Message:
        # TODO: integrate with LLM for script generation
        return message.reply(
            content="[Writer] 已收到写作任务，开始创作...",
            msg_type=MessageType.RESULT,
        )
