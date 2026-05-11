"""Director agent — task decomposition and orchestration.

The Director is responsible for:
- Receiving a high-level goal or story request
- Decomposing it into sub-tasks for other agents
- Coordinating the overall workflow
- Synthesizing final results
"""

from __future__ import annotations

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class DirectorAgent(Agent):
    """Orchestrator agent that decomposes tasks and coordinates other agents."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        config = config or AgentConfig(
            name="director",
            description="Task decomposition and orchestration agent",
        )
        super().__init__(config)

    def system_prompt(self) -> str:
        return (
            "你是一个视觉小说项目的导演（Director）。"
            "你的职责是：\n"
            "1. 分析用户的高层需求\n"
            "2. 将任务分解为子任务，分配给 Writer、Artist 等角色\n"
            "3. 协调整体工作流程，确保各环节衔接\n"
            "4. 汇总结果，生成最终输出\n\n"
            "请始终以结构化的方式输出你的分解计划。"
        )

    async def run(self, message: Message) -> Message:
        # TODO: integrate with LLM for actual task decomposition
        return message.reply(
            content="[Director] 已收到任务，开始分解...",
            msg_type=MessageType.CONTROL,
        )
