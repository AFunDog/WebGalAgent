# browser 模块

基于 Playwright 的浏览器自动化与确定性视频录制模块，为 WebGal Agent 提供页面操控、脚本注入和逐帧录制能力。

## 架构概览

```
browser/
├── __init__.py       # 模块导出
├── client.py         # BrowserClient — 浏览器生命周期与页面操作
├── models.py         # Pydantic 数据模型（配置、状态、结果）
├── recorder.py       # VideoRecorder — CDP + FFmpeg 逐帧确定性录制
├── capture.py        # CanvasCapture — CCapture.js 方案（旧版，保留兼容）
├── tools.py          # Agent 工具封装（navigate/click/fill/screenshot/get_text/wait_for）
├── demo.py           # 命令行演示入口
└── assets/           # CCapture.js / html2canvas 静态资源
```

### 核心流程

```
BrowserClient
  │
  ├── add_script_injection()   ← 页面加载前拦截 JS，注入自定义代码
  ├── navigate()                ← 导航到目标页面
  ├── wait_for() / click() ...  ← 页面交互
  │
  └── create_cdp_session()      ← 建立 CDP 连接
        │
        ▼
VideoRecorder
  │
  ├── Emulation.setVirtualTimePolicy("pause")   ← 冻结虚拟时间
  ├── HeadlessExperimental.beginFrame(...)       ← 逐帧推进 + 截图
  │       │
  │       └── base64 PNG → FFmpeg stdin          ← 管道编码
  │
  └── 输出 MP4 (libx264 / CRF 18)
```

## 关键组件

### 1. BrowserClient (`client.py`)

Playwright 浏览器的异步封装，核心能力：

| 方法 | 说明 |
|---|---|
| `new_context()` | 创建浏览器上下文，支持 `executable_path` 指定自定义浏览器 |
| `add_script_injection()` | 拦截指定 URL 的响应，在 JS 文件末尾注入代码 |
| `create_cdp_session()` | 创建 CDP Session 用于底层协议操作 |
| `navigate()` | 导航到 URL，支持 `wait_until` 参数 |
| `click()` / `fill()` / `get_text()` | 元素交互 |
| `screenshot()` | 页面截图 |
| `wait_for()` | 等待元素状态变化 |

**虚拟时间控制**（用于 JS 侧确定性渲染）：

| 方法 | 说明 |
|---|---|
| `enable_time_control(fps)` | Hook `performance.now`/`Date.now`/`requestAnimationFrame` |
| `prepare_time_control(fps)` | 通过 `add_init_script` 在导航前注入，确保先于页面脚本执行 |
| `advance_frame(count)` | 推进虚拟时间 N 帧 |
| `disable_time_control()` | 恢复原生时间函数 |

### 2. VideoRecorder (`recorder.py`)

**CDP + FFmpeg** 逐帧确定性录制方案：

1. 通过 `Emulation.setVirtualTimePolicy("pause")` 冻结浏览器虚拟时间
2. 循环调用 `HeadlessExperimental.beginFrame`，指定 `frameTimeTicks` 和 `interval` 推进时间并获取截图
3. 解码 base64 PNG 数据，通过 stdin 管道喂给 FFmpeg 编码为 MP4
4. 无新帧时复用上一帧（`last_frame` fallback）

特点：
- **确定性**：每帧的虚拟时间精确控制，不受系统负载影响
- **高效**：无需等待真实时间，录制速度取决于 CPU（通常数倍于实时）
- **高质量**：libx264 + CRF 18 + slow preset

### 3. 脚本拦截注入 (`add_script_injection`)

通过 Playwright `page.route()` 拦截匹配的 JS 请求，在原始响应末尾追加自定义代码：

```python
await client.add_script_injection(
    url_pattern="**/index-e1b3c40e.js",
    inject_code="window.changeScene = gCe;\nwindow.toggleAuto = wU;",
)
```

- 在 `navigate()` 之前调用
- 支持 glob 模式匹配（如 `**/*.js`）
- 拦截失败时自动降级放行原始请求

## 使用方式

### 前置依赖

```bash
# 1. 安装 Playwright 浏览器
playwright install chromium

# 2. 确保 FFmpeg 在系统 PATH 中
ffmpeg -version

# 3. （可选）下载 chrome-headless-shell 用于确定性录制
#    https://googlechromelabs.github.io/chrome-for-testing/
```

### 命令行演示

```bash
# 导航截图模式
python -m webgal_agent.browser.demo navigate --url https://example.com

# 录制模式（默认 chromium）
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --duration 10 \
    --fps 30

# 使用 chrome-headless-shell（推荐用于确定性录制）
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --executable "D:\Program\chrome-headless-shell-win64\chrome-headless-shell.exe" \
    --headless

# 仅观察页面，不录制
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --no-record \
    --duration 5

# 自定义选择器
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --selector "div._MainStage_main_9enex_1"
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `mode` | 必填 | `navigate` 或 `record` |
| `--url` | `https://example.com` | 目标 URL |
| `--output` | `data/temp/output.mp4` | 输出路径 |
| `--duration` | `5.0` | 录制时长（秒） |
| `--fps` | `30.0` | 帧率 |
| `--selector` | `div._MainStage_main_9enex_1` | 录制目标 CSS 选择器，`auto` 自动检测 |
| `--browser` | `chromium` | 浏览器引擎：chromium / firefox / webkit |
| `--executable` | — | 自定义浏览器可执行文件路径 |
| `--headless` | `False` | 无头模式 |
| `--no-record` | `False` | 跳过录制，仅等待观察 |

### 编程接口

```python
import asyncio
from webgal_agent.browser import (
    BrowserClient,
    DefaultBrowserConfig,
    VideoRecorder,
    Selector,
    SelectorType,
)
from webgal_agent.browser.models import CaptureConfig, VideoConfig


async def main():
    config = DefaultBrowserConfig(
        browser_type="chromium",
        headless=True,
        executable_path="D:/Program/chrome-headless-shell-win64/chrome-headless-shell.exe",
    )

    async with BrowserClient(config) as client:
        # 1. 注入脚本（在导航前）
        await client.add_script_injection(
            url_pattern="**/index-e1b3c40e.js",
            inject_code="window.changeScene = gCe;\nwindow.toggleAuto = wU;",
        )

        # 2. 导航
        await client.navigate("http://localhost:3000", wait_until="load")

        # 3. 页面交互
        page = await client.get_page()
        await page.wait_for_function(
            "() => typeof window.changeScene === 'function'",
            timeout=10000,
        )
        await page.evaluate('() => window.changeScene("场景路径", 1)')

        # 4. 创建 CDP Session + 录制
        cdp = await client.create_cdp_session()

        recorder = VideoRecorder(
            cdp_session=cdp,
            page=page,
            video_config=VideoConfig(output_path="output.mp4", fps=30),
            capture_config=CaptureConfig(
                fps=30,
                canvas_selector="div._MainStage_main_9enex_1",
                max_duration=10.0,
            ),
        )
        result = await recorder.start()

        print(f"录制完成: {result.total_frames} 帧, "
              f"视频 {result.duration:.1f}s, "
              f"实际耗时 {result.wall_time:.1f}s, "
              f"时间比 {result.duration / result.wall_time:.2f}x")


asyncio.run(main())
```

### Agent 工具

`tools.py` 将浏览器操作封装为 Agent 可调用的 Tool：

| 工具 | 说明 |
|---|---|
| `NavigateTool` | 导航到 URL |
| `ClickTool` | 点击元素 |
| `FillTool` | 填写表单 |
| `GetTextTool` | 获取元素文本 |
| `ScreenshotTool` | 页面截图 |
| `WaitForTool` | 等待元素状态 |

```python
from webgal_agent.browser import BrowserClient, DefaultBrowserConfig
from webgal_agent.browser.tools import NavigateTool, ClickTool

client = BrowserClient(DefaultBrowserConfig())
navigate = NavigateTool(client)
result = await navigate.execute(url="https://example.com")
```

## 两种录制方案对比

| | CDP + FFmpeg (`VideoRecorder`) | CCapture.js (`CanvasCapture`) |
|---|---|---|
| 时间控制 | CDP `Emulation.setVirtualTimePolicy` | JS Hook `performance.now`/`Date.now` |
| 截图方式 | `HeadlessExperimental.beginFrame` | `canvas.toDataURL` / `html2canvas` |
| 编码 | FFmpeg 管道 (libx264) | 浏览器端 WebM 编码 |
| 确定性 | 高（引擎级控制） | 中（依赖 JS Hook 时序） |
| 输出格式 | MP4 (H.264) | WebM |
| 推荐场景 | 生产录制 | 旧版兼容 |

## 选择器自动检测

`--selector auto` 模式按优先级检测可录制目标：

1. `div._MainStage_main_9enex_1` — WebGal 主舞台
2. `#root` — 通用根元素
3. `canvas` — Canvas 元素

首个可见元素将被选为录制目标。
