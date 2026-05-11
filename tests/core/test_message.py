"""Tests for the Message model."""

from __future__ import annotations

from webgal_agent.core.message import Message, MessageType


def test_message_creation() -> None:
    msg = Message(sender="a", receiver="b", content="hi")
    assert msg.type == MessageType.TASK
    assert msg.sender == "a"
    assert msg.receiver == "b"


def test_message_reply() -> None:
    msg = Message(sender="a", receiver="b", content="hi")
    reply = msg.reply(content="hello")
    assert reply.sender == "b"
    assert reply.receiver == "a"
    assert reply.type == MessageType.RESULT


def test_message_with_type() -> None:
    msg = Message(sender="a", receiver="b", content="hi")
    error_msg = msg.with_type(MessageType.ERROR)
    assert error_msg.type == MessageType.ERROR
