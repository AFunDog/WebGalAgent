"""多智能体框架核心抽象。"""

from webgal_agent.core.agent import Agent, AgentState
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.memory import Memory, InMemoryMemory

__all__ = [
    "Agent",
    "AgentState",
    "Message",
    "MessageType",
    "Memory",
    "InMemoryMemory",
]
