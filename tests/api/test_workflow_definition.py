"""共享工作流定义的基础测试。"""

from __future__ import annotations

from webgal_agent.api.workflow_definition import (
    AGENT_DESCRIPTIONS,
    AGENT_PREV_DEPS,
    PIPELINE_ORDER,
)


def test_pipeline_order_is_expected() -> None:
    assert PIPELINE_ORDER == ["outline_writer", "script_writer", "script_converter"]


def test_all_pipeline_steps_have_descriptions() -> None:
    assert set(PIPELINE_ORDER) <= set(AGENT_DESCRIPTIONS)
    for step in PIPELINE_ORDER:
        assert AGENT_DESCRIPTIONS[step]


def test_script_converter_only_depends_on_script_writer() -> None:
    assert AGENT_PREV_DEPS["script_converter"] == ["script_writer"]
    assert AGENT_PREV_DEPS["outline_writer"] is None
