"""WebGal 专属录制准备流程。"""

from __future__ import annotations

from collections.abc import Callable

from webgal_agent.browser.webgal_injection import (
    APPLY_GAME_CONFIG_JS,
    CHANGE_SCENE_JS,
    NAVIGATE_INJECT_CODE,
    POST_SCENE_PREPARE_JS,
    RECORD_INJECT_CODE,
    WAIT_FOR_WEBGAL_READY_JS,
    WEBGAL_SCRIPT_URL_PATTERN,
)

LogFn = Callable[[str], None]


async def install_webgal_injection(client, *, record_mode: bool, log: LogFn) -> None:
    """安装 WebGal 构建产物拦截注入。"""
    inject_code = RECORD_INJECT_CODE if record_mode else NAVIGATE_INJECT_CODE
    log(f"拦截 WebGal 脚本注入 ({WEBGAL_SCRIPT_URL_PATTERN})...")
    await client.add_script_injection(
        url_pattern=WEBGAL_SCRIPT_URL_PATTERN,
        inject_code=inject_code,
    )


async def apply_game_config(page, overrides: dict[str, int], *, log: LogFn) -> None:
    """通过 page.evaluate 执行 IndexedDB 游戏配置修改脚本。"""
    log(f"修改游戏配置: {overrides}")
    success = await page.evaluate(APPLY_GAME_CONFIG_JS, overrides)
    log(f"游戏配置{'已更新' if success else '更新失败'}")


async def prepare_webgal_recording(
    page,
    *,
    scene_path: str,
    game_config: dict[str, int] | None,
    log: LogFn,
) -> None:
    """执行 WebGal 页面专属准备。"""
    log("等待 changeScene 函数就绪...")
    await page.wait_for_function(WAIT_FOR_WEBGAL_READY_JS, timeout=10000)
    log(f'changeScene 已就绪，调用 changeScene("{scene_path}", 1)...')
    await page.evaluate(CHANGE_SCENE_JS, scene_path)
    log("changeScene 调用完成")

    if game_config:
        log("场景切换后注入游戏配置...")
        await apply_game_config(page, game_config, log=log)

    await page.evaluate(POST_SCENE_PREPARE_JS)
