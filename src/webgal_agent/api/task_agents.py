"""TaskManager 使用的 agent 构建与展示辅助。"""

from __future__ import annotations

from pathlib import Path

from webgal_agent.agents import OutlineWriterAgent, ScriptConverterAgent, ScriptWriterAgent
from webgal_agent.api.task_state import AgentInfoDict
from webgal_agent.api.workflow_definition import AGENT_DESCRIPTIONS, PIPELINE_ORDER
from webgal_agent.config.provider_manager import ProviderConfigManager
from webgal_agent.core.agent import Agent
from webgal_agent.tools.base import Tool


def build_agents(
    prompts: dict[str, str],
    provider_manager: ProviderConfigManager | None,
    task_dir: str | Path,
    task_id: str = "",
) -> dict[str, Agent]:
    """构建流水线运行所需的全部 agent。"""
    from webgal_agent.tools.asset_query import AssetQueryTool
    from webgal_agent.tools.file_ops import ReadFileTool, WriteResultTool
    from webgal_agent.tools.read_model import ReadModelTool

    result_dir = str(Path(task_dir) / task_id / "result") if task_id else None
    read_file_tool = ReadFileTool(result_dir=result_dir)

    asset_tool = AssetQueryTool()
    read_model_tool = ReadModelTool()
    write_result_tool = WriteResultTool(task_id=task_id, task_dir=task_dir) if task_id else None

    agent_tools: dict[str, list[Tool]] = {
        "outline_writer": [],
        "script_writer": [],
        "script_converter": [
            read_file_tool,
            asset_tool,
            read_model_tool,
        ] + ([write_result_tool] if write_result_tool else []),
    }

    agents: dict[str, Agent] = {}
    for name in PIPELINE_ORDER:
        if provider_manager:
            config = provider_manager.to_agent_config(name, AGENT_DESCRIPTIONS.get(name, ""))
        else:
            from webgal_agent.core.agent import AgentConfig

            config = AgentConfig(name=name, description=AGENT_DESCRIPTIONS.get(name, ""))

        tools = agent_tools.get(name, [])
        prompt = prompts.get(name, "")

        if name == "outline_writer":
            agents[name] = OutlineWriterAgent(config=config, system_prompt=prompt, tools=tools)
        elif name == "script_writer":
            agents[name] = ScriptWriterAgent(config=config, system_prompt=prompt, tools=tools)
        elif name == "script_converter":
            agents[name] = ScriptConverterAgent(config=config, system_prompt=prompt, tools=tools)
    return agents


def build_agent_info(agents: dict[str, Agent]) -> list[AgentInfoDict]:
    """将 agent 实例映射成 API 友好的响应结构。"""
    return [
        {
            "name": agent.name,
            "description": agent.description,
            "state": agent.state.value,
            "provider": agent._config.provider,
            "model": agent._config.model,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in agent.tools.values()
            ],
        }
        for agent in agents.values()
    ]
