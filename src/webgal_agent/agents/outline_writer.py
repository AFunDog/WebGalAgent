"""智能体 A：大纲编写器。

接收用户输入和知识库，生成剧本大纲。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
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
        super().__init__(config, tools=tools, system_prompt=system_prompt)
