"""当前 browser 模块的基础单元测试。"""

from __future__ import annotations

from webgal_agent.browser.models import RecordingResult, Selector, SelectorType, VideoConfig
from webgal_agent.browser.paths import default_recording_log_path
from webgal_agent.browser.script_loader import load_browser_script
from webgal_agent.browser.webgal_injection import (
    AUTO_SELECTOR_CANDIDATES,
    CHANGE_SCENE_JS,
    NAVIGATE_INJECT_CODE,
    RECORD_INJECT_CODE,
    WAIT_FOR_WEBGAL_READY_JS,
    WEBGAL_SCRIPT_URL_PATTERN,
)


def test_video_config_defaults() -> None:
    config = VideoConfig(output_path="test.mp4")
    assert config.fps == 30.0
    assert config.codec == "webm"
    assert config.quality == 17


def test_selector_defaults() -> None:
    selector = Selector(value="#root")
    assert selector.type == SelectorType.CSS
    assert selector.value == "#root"


def test_recording_result_fields() -> None:
    result = RecordingResult(
        output_path="out.mp4",
        total_frames=10,
        duration=1.5,
        actual_fps=6.7,
        file_size_mb=2.5,
    )
    assert result.total_frames == 10
    assert result.has_audio is False
    assert result.output_fps == 0.0
    assert result.log_path is None


def test_webgal_injection_constants_are_current() -> None:
    assert WEBGAL_SCRIPT_URL_PATTERN == "**/index-e1b3c40e.js"
    assert AUTO_SELECTOR_CANDIDATES == ("#root", "canvas")
    assert "window.changeScene = gCe;" in NAVIGATE_INJECT_CODE
    assert "window.saveConfig = _r;" in RECORD_INJECT_CODE
    assert "typeof window.changeScene === 'function'" in WAIT_FOR_WEBGAL_READY_JS
    assert "window.changeScene(path, 1);" in CHANGE_SCENE_JS


def test_default_log_path_helper_is_current() -> None:
    assert str(default_recording_log_path(VideoConfig(output_path="out.mp4").output_path)) == "out.mp4.log"


def test_browser_scripts_load_from_js_directory() -> None:
    webaudio_capture = load_browser_script("webaudio_capture.js")

    assert "window.__startTrackProcessor" in webaudio_capture
