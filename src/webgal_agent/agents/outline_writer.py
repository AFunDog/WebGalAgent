"""智能体 A：大纲编写器。

接收用户输入和知识库，生成剧本大纲。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType
from webgal_agent.tools.base import Tool


class OutlineWriterAgent(Agent):
    """智能体 A：编写剧本大纲。

    输入: 用户初始输入 + 知识库
    输出: 剧本大纲
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        system_prompt: str = "",
        tools: list[Tool] | None = None,
    ) -> None:
        config = config or AgentConfig(
            name="outline_writer",
            description="接受用户输入和知识库，编写剧本大纲",
        )
        super().__init__(config, tools=tools)
        self._custom_prompt = system_prompt

    def system_prompt(self) -> str:
        if self._custom_prompt:
            return self._custom_prompt
        return "TODO: 请在 configs/prompts.yaml 中配置 outline_writer 的系统提示词"

    async def run(self, message: Message) -> Message:
        response = await self._call_llm_with_tools(
            system_prompt=self.system_prompt(),
            user_content=message.content,
        )
        metadata = dict(message.metadata)
        if response.tool_calls:
            metadata["tool_calls"] = [
                {"tool": tc.tool_name, "args": tc.arguments, "result": tc.result, "success": tc.success}
                for tc in response.tool_calls
            ]
        return message.reply(content=response.content, msg_type=MessageType.RESULT).model_copy(
            update={"metadata": metadata}
        )
