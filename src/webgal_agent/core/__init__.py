"""Core abstractions for the multi-agent framework."""

from webgal_agent.core.agent import Agent, AgentState
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.workflow import Workflow, WorkflowResult
from webgal_agent.core.memory import Memory, InMemoryMemory

__all__ = [
    "Agent",
    "AgentState",
    "Message",
    "MessageType",
    "Workflow",
    "WorkflowResult",
    "Memory",
    "InMemoryMemory",
]
