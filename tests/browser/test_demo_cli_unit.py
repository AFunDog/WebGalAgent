"""demo_cli 的纯单元测试。"""

from __future__ import annotations

import argparse
from pathlib import Path

from webgal_agent.browser.demo_cli import build_parser, run_cli


def test_build_parser_accepts_save_logs_flag() -> None:
    parser = build_parser()

    args = parser.parse_args([
        "record",
        "--url", "http://localhost:3001",
        "--page-mode", "generic",
        "--save-logs",
        "--record-audio",
        "--executable", "C:/Browser/chrome.exe",
    ])

    assert args.mode == "record"
    assert args.page_mode == "generic"
    assert args.save_logs is True
    assert args.record_audio is True
    assert args.executable == "C:/Browser/chrome.exe"


def test_run_cli_record_mode_passes_record_options(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_demo_record(**kwargs):
        captured.update(kwargs)
        return {"success": True, "message": "ok"}

    monkeypatch.setattr("webgal_agent.browser.demo_cli.demo_record", fake_demo_record)

    args = argparse.Namespace(
        mode="record",
        url="http://localhost:3001",
        output="data/browser/recordings/out.mp4",
        duration=2.0,
        fps=30.0,
        width=1280,
        height=720,
        page_mode="generic",
        selector="#root",
        scene_path="index.txt",
        stop_condition="window.done",
        browser="msedge",
        headless=True,
        no_record=False,
        screencast_quality=85,
        save_frames="data/browser/temp/frames",
        format="png",
        executable="C:/Browser/chrome.exe",
        record_audio=True,
        save_logs=True,
        game_config='{"optionData.autoSpeed": 50}',
        json_mode=False,
    )

    run_cli(args)

    assert captured["url"] == "http://localhost:3001"
    assert captured["page_mode"] == "generic"
    assert captured["selector"] == "#root"
    assert captured["stop_condition"] == "window.done"
    assert captured["record_audio"] is True
    assert captured["executable_path"] == "C:/Browser/chrome.exe"
    assert Path(str(captured["log_path"])) == Path("data/browser/recordings/out.mp4.log")
    assert captured["game_config"] == {"optionData.autoSpeed": 50}
