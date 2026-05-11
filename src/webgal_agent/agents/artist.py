"""Artist agent — visual asset description and management.

The Artist is responsible for:
- Describing visual scene compositions
- Generating image prompts for AI art tools
- Managing character appearance descriptions
- Defining background and CG scene layouts
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class ArtistAgent(Agent):
    """Agent that handles visual asset descriptions and prompts."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        config = config or AgentConfig(
            name="artist",
            description="Visual asset description and management agent",
        )
        super().__init__(config)

    def system_prompt(self) -> str:
        return (
            "你是一个视觉小说的美术指导（Artist）。"
            "你的职责是：\n"
            "1. 根据剧本需求描述场景构图\n"
            "2. 生成角色立绘的提示词（prompt）\n"
            "3. 定义背景和 CG 的视觉风格\n"
            "4. 确保视觉资产与叙事风格一致\n\n"
            "输出应包含详细的视觉描述和可用于 AI 绘图的英文提示词。"
        )

    async def run(self, message: Message) -> Message:
        # TODO: integrate with LLM for visual description generation
        return message.reply(
            content="[Artist] 已收到美术需求，开始设计视觉描述...",
            msg_type=MessageType.RESULT,
        )
