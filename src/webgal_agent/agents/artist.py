"""Artist agent — visual and creative asset generation.

The Artist is responsible for:
- Describing visual compositions and layouts
- Generating prompts for creative tools
- Managing visual style definitions
- Ensuring creative consistency
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class ArtistAgent(Agent):
    """Agent that handles creative and visual asset generation."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        config = config or AgentConfig(
            name="artist",
            description="Visual asset description and management agent",
        )
        super().__init__(config)

    def system_prompt(self) -> str:
        return (
            "你是一个创意资产专家（Artist）。"
            "你的职责是：\n"
            "1. 根据需求描述视觉构图和创意方案\n"
            "2. 生成可用的提示词（prompt）\n"
            "3. 定义视觉风格和规范\n"
            "4. 确保创意资产与整体风格一致\n\n"
            "输出应包含详细的描述和可操作的提示词。"
        )

    async def run(self, message: Message) -> Message:
        # TODO: integrate with LLM for visual description generation
        return message.reply(
            content="[Artist] 已收到美术需求，开始设计视觉描述...",
            msg_type=MessageType.RESULT,
        )
