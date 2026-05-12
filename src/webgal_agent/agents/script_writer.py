"""智能体 B：剧本编写器。

接收用户输入、大纲和知识库，生成各章节剧本。
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.tools.base import Tool


class ScriptWriterAgent(Agent):
    """智能体 B：生成章节剧本。

    输入: 用户初始输入 + A 生成的大纲 + 知识库
    输出: 各章节剧本
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        system_prompt: str = "",
        tools: list[Tool] | None = None,
    ) -> None:
        config = config or AgentConfig(
            name="script_writer",
            description="接受用户输入、剧本大纲和知识库，生成各章节剧本",
        )
        super().__init__(config, tools=tools, system_prompt=system_prompt)
