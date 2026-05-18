"""record 路由中的纯单元测试。"""

from __future__ import annotations

import pytest

from webgal_agent.api.routes.record import (
    RecordConfigRequest,
    _build_cli_args,
    get_record_config,
)


def test_build_cli_args_includes_optional_flags() -> None:
    req = RecordConfigRequest(
        url="http://localhost:3001",
        duration=3.5,
        fps=60,
        canvas_selector="#root",
        scene_path="start.txt",
        stop_condition="window.done === true",
        browser_type="msedge",
        headless=True,
        viewport_width=1280,
        viewport_height=720,
        format="png",
        quality=80,
        record_audio=True,
        executable_path="C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        game_config={"optionData.autoSpeed": 50},
    )

    args = _build_cli_args(req, "data/temp/out.mp4")

    assert args[:4] == [args[0], "-m", "webgal_agent.browser.demo", "record"]
    assert "--url" in args and "http://localhost:3001" in args
    assert "--duration" in args and "3.5" in args
    assert "--stop-on" in args and "window.done === true" in args
    assert "--headless" in args
    assert "--record-audio" in args
    assert "--executable" in args
    assert "C:/Program Files/Microsoft/Edge/Application/msedge.exe" in args
    assert "--game-config" in args
    assert "--json" in args


def test_build_cli_args_omits_zero_duration_and_empty_optional_fields() -> None:
    req = RecordConfigRequest(url="https://example.com")
    args = _build_cli_args(req, "out.mp4")

    assert "--duration" not in args
    assert "--stop-on" not in args
    assert "--headless" not in args
    assert "--record-audio" not in args
    assert "--game-config" not in args


@pytest.mark.asyncio
async def test_get_record_config_uses_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "webgal_agent.api.routes.record._record_defaults",
        lambda: {
            "url": "http://localhost:3001",
            "format": "png",
            "quality": 75,
            "fps": 24,
            "duration": 6,
            "canvas_selector": "#root",
            "scene_path": "opening.txt",
            "stop_condition": "window.done",
            "browser_type": "chromium",
            "headless": True,
            "viewport_width": 1280,
            "viewport_height": 720,
            "record_audio": True,
            "game_config": {"optionData.autoSpeed": 40},
        },
    )

    result = await get_record_config()

    assert result["url"] == "http://localhost:3001"
    assert result["format"] == "png"
    assert result["quality"] == 75
    assert result["canvas_selector"] == "#root"
    assert result["record_audio"] is True
    assert result["executable_path"] == ""
    assert result["game_config"] == {"optionData.autoSpeed": 40}
