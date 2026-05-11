"""智能体 C：脚本转换器。

接收用户输入、剧本和知识库，转换为 WebGal 引擎格式。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class ScriptConverterAgent(Agent):
    """智能体 C：转换为 WebGal 脚本。

    输入: 用户初始输入 + B 生成的剧本 + 知识库
    输出: WebGal 引擎可识别的动画脚本
    """

    def __init__(self, config: AgentConfig | None = None, system_prompt: str = "") -> None:
        config = config or AgentConfig(
            name="script_converter",
            description="接受用户输入、剧本和知识库，转换为 WebGal 引擎脚本",
        )
        super().__init__(config)
        self._custom_prompt = system_prompt

    def system_prompt(self) -> str:
        if self._custom_prompt:
            return self._custom_prompt
        return "TODO: 请在 configs/prompts.yaml 中配置 script_converter 的系统提示词"

    async def run(self, message: Message) -> Message:
        # TODO: 对接 LLM
        return message.reply(
            content="[ScriptConverter] 已收到剧本和知识库，开始转换为 WebGal 脚本...",
            msg_type=MessageType.RESULT,
        )
