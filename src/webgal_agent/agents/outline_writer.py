"""智能体 A：大纲编写器。

接收用户输入和知识库，生成剧本大纲。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class OutlineWriterAgent(Agent):
    """智能体 A：编写剧本大纲。

    输入: 用户初始输入 + 知识库
    输出: 剧本大纲
    """

    def __init__(self, config: AgentConfig | None = None, system_prompt: str = "") -> None:
        config = config or AgentConfig(
            name="outline_writer",
            description="接受用户输入和知识库，编写剧本大纲",
        )
        super().__init__(config)
        self._custom_prompt = system_prompt

    def system_prompt(self) -> str:
        if self._custom_prompt:
            return self._custom_prompt
        return "TODO: 请在 configs/prompts.yaml 中配置 outline_writer 的系统提示词"

    async def run(self, message: Message) -> Message:
        # TODO: 对接 LLM
        return message.reply(
            content="[OutlineWriter] 已收到用户输入和知识库，开始编写剧本大纲...",
            msg_type=MessageType.RESULT,
        )
