"""流水线工作流的共享定义。

集中维护步骤顺序、步骤描述和前序依赖，避免后端不同模块各自复制
同一套工作流元数据。
"""

from __future__ import annotations

PIPELINE_ORDER = ["outline_writer", "script_writer", "script_converter"]

AGENT_DESCRIPTIONS: dict[str, str] = {
    "outline_writer": "接受用户输入和知识库，编写剧本大纲",
    "script_writer": "接受用户输入、剧本大纲和知识库，生成各章节剧本",
    "script_converter": "接受用户输入、剧本和知识库，转换为 WebGal 引擎脚本",
}

# None 表示默认注入所有前序步骤输出。
AGENT_PREV_DEPS: dict[str, list[str] | None] = {
    "outline_writer": None,
    "script_writer": None,
    "script_converter": ["script_writer"],
}
