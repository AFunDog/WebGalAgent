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
        page_mode="generic",
        stop_condition="window.done === true",
        browser_type="msedge",
        headless=True,
        viewport_width=1280,
        viewport_height=720,
        format="png",
        quality=80,
        record_audio=True,
        av_sync_debug_interval=2.0,
        av_sync_debug_flash_ms=140,
        av_sync_debug_tone_ms=160,
        av_sync_debug_frequency=660.0,
        executable_path="C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        save_logs=True,
        game_config={"optionData.autoSpeed": 50},
    )

    args = _build_cli_args(req, "data/browser/recordings/out.mp4")

    assert args[:4] == [args[0], "-m", "webgal_agent.browser.demo", "record"]
    assert "--url" in args and "http://localhost:3001" in args
    assert "--page-mode" in args and "generic" in args
    assert "--duration" in args and "3.5" in args
    assert "--stop-on" in args and "window.done === true" in args
    assert "--headless" in args
    assert "--record-audio" in args
    assert "--av-sync-debug-interval" in args and "2.0" in args
    assert "--av-sync-debug-flash-ms" in args and "140" in args
    assert "--av-sync-debug-tone-ms" in args and "160" in args
    assert "--av-sync-debug-frequency" in args and "660.0" in args
    assert "--executable" in args
    assert "C:/Program Files/Microsoft/Edge/Application/msedge.exe" in args
    assert "--save-logs" in args
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
    assert "--save-logs" not in args


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
            "page_mode": "generic",
            "stop_condition": "window.done",
            "browser_type": "chromium",
            "headless": True,
            "viewport_width": 1280,
            "viewport_height": 720,
            "record_audio": True,
            "av_sync_debug_interval": 1.5,
            "av_sync_debug_flash_ms": 100,
            "av_sync_debug_tone_ms": 150,
            "av_sync_debug_frequency": 523.25,
            "game_config": {"optionData.autoSpeed": 40},
        },
    )

    result = await get_record_config()

    assert result["url"] == "http://localhost:3001"
    assert result["format"] == "png"
    assert result["quality"] == 75
    assert result["canvas_selector"] == "#root"
    assert result["page_mode"] == "generic"
    assert result["record_audio"] is True
    assert result["av_sync_debug_interval"] == 1.5
    assert result["av_sync_debug_flash_ms"] == 100
    assert result["av_sync_debug_tone_ms"] == 150
    assert result["av_sync_debug_frequency"] == 523.25
    assert result["executable_path"] == ""
    assert result["save_logs"] is False
    assert result["game_config"] == {"optionData.autoSpeed": 40}
