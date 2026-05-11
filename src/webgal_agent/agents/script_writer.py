"""智能体 B：剧本编写器。

接收用户输入、大纲和知识库，生成各章节剧本。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class ScriptWriterAgent(Agent):
    """智能体 B：生成章节剧本。

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
        result = await self._call_llm(
            system_prompt=self.system_prompt(),
            user_content=message.content,
        )
        return message.reply(content=result, msg_type=MessageType.RESULT)
