"""Writer agent — script and dialogue generation.

The Writer is responsible for:
- Generating story scripts and dialogues
- Adapting narrative style and tone
- Creating branching narrative paths
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class WriterAgent(Agent):
    """Agent that generates visual novel scripts and dialogues."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        config = config or AgentConfig(
            name="writer",
            description="Script and dialogue generation agent",
        )
        super().__init__(config)

    def system_prompt(self) -> str:
        return (
            "你是一个视觉小说的剧作家（Writer）。"
            "你的职责是：\n"
            "1. 根据导演的分解任务编写剧本\n"
            "2. 创作生动的对话和叙事文本\n"
            "3. 设计分支剧情选项\n"
            "4. 保持角色性格一致性\n\n"
            "输出格式应兼容 WebGal 引擎的脚本格式。"
        )

    async def run(self, message: Message) -> Message:
        # TODO: integrate with LLM for script generation
        return message.reply(
            content="[Writer] 已收到写作任务，开始创作...",
            msg_type=MessageType.RESULT,
        )
