"""智能体 C：脚本转换器。

接收用户输入、剧本和知识库，转换为 WebGal 引擎格式。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.tools.base import Tool


class ScriptConverterAgent(Agent):
    """智能体 C：转换为 WebGal 脚本。

    输入: 用户初始输入 + B 生成的剧本 + 知识库
    输出: WebGal 引擎可识别的动画脚本
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        system_prompt: str = "",
        tools: list[Tool] | None = None,
    ) -> None:
        config = config or AgentConfig(
            name="script_converter",
            description="接受用户输入、剧本和知识库，转换为 WebGal 引擎脚本",
        )
        super().__init__(config, tools=tools, system_prompt=system_prompt)
