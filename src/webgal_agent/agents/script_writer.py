"""Agent B: Script Writer.

Receives user input + outline from A + knowledge base,
generates chapter-by-chapter scripts.
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class ScriptWriterAgent(Agent):
    """Agent B: 生成章节剧本.

    输入: 用户初始输入 + A 生成的大纲 + 知识库
    输出: 各章节剧本
    """

    def __init__(self, config: AgentConfig | None = None, system_prompt: str = "") -> None:
        config = config or AgentConfig(
            name="script_writer",
            description="接受用户输入、剧本大纲和知识库，生成各章节剧本",
        )
        super().__init__(config)
        self._custom_prompt = system_prompt

    def system_prompt(self) -> str:
        if self._custom_prompt:
            return self._custom_prompt
        return "TODO: 请在 configs/prompts.yaml 中配置 script_writer 的系统提示词"

    async def run(self, message: Message) -> Message:
        # TODO: integrate with LLM
        return message.reply(
            content="[ScriptWriter] 已收到大纲和知识库，开始生成章节剧本...",
            msg_type=MessageType.RESULT,
        )
