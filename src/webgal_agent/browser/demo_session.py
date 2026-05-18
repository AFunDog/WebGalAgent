"""demo CLI 的导航与录制会话实现。"""

from __future__ import annotations

import asyncio

from webgal_agent.browser import (
    BrowserClient,
    DefaultBrowserConfig,
    ScreencastRecorder,
    Selector,
    SelectorType,
)
from webgal_agent.browser.models import VideoConfig
from webgal_agent.browser.paths import default_demo_screenshot_path
from webgal_agent.browser.webgal_injection import (
    APPLY_GAME_CONFIG_JS,
    AUTO_SELECTOR_CANDIDATES,
    CHANGE_SCENE_JS,
    NAVIGATE_INJECT_CODE,
    POST_SCENE_PREPARE_JS,
    RECORD_INJECT_CODE,
    WAIT_FOR_WEBGAL_READY_JS,
    WEBGAL_SCRIPT_URL_PATTERN,
)


def log_message(msg: str, *, json_mode: bool = False) -> None:
    """json 模式下日志输出到 stderr，避免污染 stdout。"""
    import sys

    if json_mode:
        print(msg, file=sys.stderr)
    else:
        print(msg)


async def apply_game_config(page, overrides: dict[str, int], *, json_mode: bool = False) -> None:
    """通过 page.evaluate 执行 IndexedDB 游戏配置修改脚本。"""
    log_message(f"修改游戏配置: {overrides}", json_mode=json_mode)
    success = await page.evaluate(APPLY_GAME_CONFIG_JS, overrides)
    log_message(f"游戏配置{'已更新' if success else '更新失败'}", json_mode=json_mode)


def _build_browser_config(
    *,
    browser_type: str,
    headless: bool,
    width: int,
    height: int,
    executable_path: str | None = None,
    record_audio: bool = False,
) -> DefaultBrowserConfig:
    launch_args = ["--autoplay-policy=no-user-gesture-required"] if record_audio else None
    return DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=width,
        viewport_height=height,
        executable_path=executable_path,
        channel="msedge" if browser_type == "msedge" else None,
        launch_args=launch_args,
    )


async def demo_navigate(
    url: str,
    browser_type: str = "chromium",
    headless: bool = False,
    width: int = 1920,
    height: int = 1080,
) -> None:
    """演示：导航并截图。"""
    config = _build_browser_config(
        browser_type=browser_type,
        headless=headless,
        width=width,
        height=height,
    )

    async with BrowserClient(config) as client:
        print(f"拦截脚本注入 ({WEBGAL_SCRIPT_URL_PATTERN})...")
        await client.add_script_injection(
            url_pattern=WEBGAL_SCRIPT_URL_PATTERN,
            inject_code=NAVIGATE_INJECT_CODE,
        )

        print(f"正在使用 {browser_type} 导航到: {url}")
        state = await client.navigate(url)
        print(f"页面标题: {state.title}")
        print(f"当前 URL: {state.url}")

        screenshot_path = default_demo_screenshot_path()
        await client.screenshot(path=str(screenshot_path), full_page=False)
        print(f"截图已保存: {screenshot_path}")

        await asyncio.sleep(2)


async def demo_record(
    url: str,
    output_path: str,
    duration: float = 5.0,
    fps: float = 60.0,
    width: int = 1920,
    height: int = 1080,
    selector: str = "auto",
    scene_path: str = "index.txt",
    stop_condition: str | None = None,
    browser_type: str = "msedge",
    headless: bool = False,
    screencast_quality: int = 90,
    no_record: bool = False,
    save_frames: str | None = None,
    format: str = "jpeg",
    record_audio: bool = False,
    executable_path: str | None = None,
    game_config: dict[str, int] | None = None,
    debug_sync: bool = False,
    sync_debug_path: str | None = None,
    json_mode: bool = False,
) -> dict | None:
    """CDP Screencast 录制。json_mode=True 时返回结果 dict。"""
    config = _build_browser_config(
        browser_type=browser_type,
        headless=headless,
        width=width,
        height=height,
        executable_path=executable_path,
        record_audio=record_audio,
    )
    video_cfg = VideoConfig(output_path=output_path, fps=fps)

    async with BrowserClient(config) as client:
        await client.new_context(context_id="default")

        if record_audio:
            log_message("注入 WebAudio 全局捕获 (masterGain 方案)...", json_mode=json_mode)
            await client.prepare_webaudio_capture()

        log_message(f"拦截脚本注入 ({WEBGAL_SCRIPT_URL_PATTERN})...", json_mode=json_mode)
        await client.add_script_injection(
            url_pattern=WEBGAL_SCRIPT_URL_PATTERN,
            inject_code=RECORD_INJECT_CODE,
        )

        log_message(f"正在使用 {browser_type} 导航到: {url}", json_mode=json_mode)
        try:
            await client.navigate(url, wait_until="load")
        except Exception as exc:
            log_message(f"导航超时，继续等待页面加载... ({exc})", json_mode=json_mode)
            await asyncio.sleep(5)

        page = await client.get_page()
        log_message("等待 changeScene 函数就绪...", json_mode=json_mode)
        await page.wait_for_function(WAIT_FOR_WEBGAL_READY_JS, timeout=10000)
        log_message(
            f'changeScene 已就绪，调用 changeScene("{scene_path}", 1)...',
            json_mode=json_mode,
        )
        await page.evaluate(CHANGE_SCENE_JS, scene_path)
        log_message("changeScene 调用完成", json_mode=json_mode)

        if game_config:
            log_message("场景切换后注入游戏配置...", json_mode=json_mode)
            await apply_game_config(page, game_config, json_mode=json_mode)

        await page.evaluate(POST_SCENE_PREPARE_JS)

        if selector == "auto":
            for candidate in AUTO_SELECTOR_CANDIDATES:
                found = await client.wait_for(
                    Selector(value=candidate, type=SelectorType.CSS),
                    state="visible",
                    timeout=3000,
                )
                if found:
                    log_message(f"目标元素已就绪: {candidate}", json_mode=json_mode)
                    break
            else:
                log_message(
                    f"警告: 未找到 {' 或 '.join(AUTO_SELECTOR_CANDIDATES)} 元素，继续录制整个页面",
                    json_mode=json_mode,
                )
        else:
            log_message(f"等待目标元素出现: {selector}", json_mode=json_mode)
            found = await client.wait_for(
                Selector(value=selector, type=SelectorType.CSS),
                state="visible",
                timeout=10000,
            )
            if not found:
                message = f"未找到目标元素 {selector}"
                log_message(f"错误: {message}", json_mode=json_mode)
                return {"success": False, "message": message} if json_mode else None

        await asyncio.sleep(1)

        if no_record:
            log_message(f"跳过录制，等待 {duration}s 观察页面状态...", json_mode=json_mode)
            await asyncio.sleep(duration)
            log_message("观察完成!", json_mode=json_mode)
            return None

        log_message(f"开始录制 {duration}s @ {fps} FPS (CDP Screencast)...", json_mode=json_mode)
        log_message(f"输出: {output_path}", json_mode=json_mode)

        recorder = ScreencastRecorder(
            client, video_cfg, screencast_quality=screencast_quality, record_audio=record_audio
        )
        result = await recorder.start(
            duration=duration,
            format=format,
            save_frames_dir=save_frames,
            stop_condition=stop_condition,
            debug_sync=debug_sync,
            sync_debug_path=sync_debug_path,
        )

        log_message("录制完成!", json_mode=json_mode)
        log_message(f"  输出路径: {result.output_path}", json_mode=json_mode)
        log_message(
            f"  源帧率: {result.source_fps:.1f} FPS → 输出帧率: {result.output_fps:.1f} FPS",
            json_mode=json_mode,
        )
        log_message(f"  总帧数: {result.total_frames}", json_mode=json_mode)
        log_message(f"  时长: {result.duration:.1f}s", json_mode=json_mode)
        log_message(f"  文件大小: {result.file_size_mb:.2f} MB", json_mode=json_mode)

        if json_mode:
            return {
                "success": True,
                "message": "录制完成",
                "output_path": str(result.output_path),
                "total_frames": result.total_frames,
                "duration": result.duration,
                "source_fps": result.source_fps,
                "output_fps": result.output_fps,
                "file_size_mb": result.file_size_mb,
                "has_audio": result.has_audio,
                "sync_debug_path": str(result.sync_debug_path) if result.sync_debug_path else None,
            }
        return None
