"""智能体工具：扩展智能体能力。"""

from webgal_agent.tools.base import Tool, ToolResult
from webgal_agent.tools.file_ops import ReadFileTool, WriteResultTool

__all__ = ["Tool", "ToolResult", "ReadFileTool", "WriteResultTool"]
