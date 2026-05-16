# browser 模块

基于 Playwright 的浏览器自动化与视频录制模块，为 WebGal Agent 提供页面操控、脚本注入和高帧率视频录制能力。

## 架构概览

```
browser/
├── __init__.py       # 模块导出
├── client.py         # BrowserClient — 浏览器生命周期与页面操作
├── models.py         # Pydantic 数据模型（配置、状态、结果）
├── screencast.py     # ScreencastRecorder — CDP Screencast + FFmpeg 录制
├── recorder.py       # VideoRecorder — CDP beginFrame 确定性录制（遗留）
├── capture.py        # CanvasCapture — CCapture.js 录制（遗留）
├── tools.py          # Agent 工具封装（navigate/click/fill/screenshot/get_text/wait_for）
└── demo.py           # 命令行演示入口
```

### 录制方案对比

| 方案 | 文件 | 原理 | 帧率 | 适用场景 |
|------|------|------|------|----------|
| **ScreencastRecorder** | `screencast.py` | CDP `Page.startScreencast` | 可达 60fps+ | **推荐**：通用录制，普通 Chromium/Edge |
| VideoRecorder | `recorder.py` | CDP `HeadlessExperimental.beginFrame` | 精确可控 | 确定性录制，需 chrome-headless-shell |
| CanvasCapture | `capture.py` | CCapture.js 浏览器内录制 | 30fps | 遗留，特定元素录制 |

### 核心流程（ScreencastRecorder）

```
BrowserClient
  │
  ├── add_script_injection()   ← 页面加载前拦截 JS，注入自定义代码
  ├── new_context()            ← 创建浏览器上下文
  ├── navigate()               ← 导航到目标页面
  ├── wait_for() / click() ... ← 页面交互
  │
  └── ScreencastRecorder
        │
        ├── create_cdp_session()                  ← 创建 CDP Session
        ├── Page.startScreencast()                ← 启动 CDP Screencast
        │     │
        │     └── JPEG/PNG 帧（从 compositor 直拉）
        │
        ├── 缓冲帧到内存
        │
        └── FFmpeg stdin 管道                     ← 编码输出
              │
              └── 输出 MP4 (libx264) / WebM (libvpx-vp9)
```

### 架构：独立子进程隔离

Web UI 录制通过独立子进程执行，与 FastAPI 完全隔离：

```
FastAPI/Uvicorn (record.py)
  │
  └── subprocess.Popen ──────────────────────────┐
        │                                         │
        └── python -m webgal_agent.browser.demo   │
              record --json --url ...             │
              │                                   │
              ├── set_event_loop_policy(Proactor) │ ← 独立 event loop
              ├── BrowserClient                   │
              ├── ScreencastRecorder              │
              └── stdout: JSON 结果                │
                                                  │
  ←── 轮询 GET /api/record/status ←──────────────┘
```

## 关键组件

### 1. BrowserClient (`client.py`)

Playwright 浏览器的异步封装，核心能力：

| 方法 | 说明 |
|---|---|
| `new_context()` | 创建浏览器上下文 |
| `add_script_injection()` | 拦截指定 URL 的响应，在 JS 文件末尾注入代码 |
| `create_cdp_session()` | 创建 CDP Session 用于底层协议操作 |
| `navigate()` | 导航到 URL，支持 `wait_until` 参数 |
| `click()` / `fill()` / `get_text()` | 元素交互 |
| `screenshot()` | 页面截图 |
| `wait_for()` | 等待元素状态变化 |
| `prepare_time_control()` | 预装虚拟时间控制脚本（确定性渲染） |
| `advance_frame()` | 逐帧推进虚拟时间 |

### 2. ScreencastRecorder (`screencast.py`)

**CDP Screencast + FFmpeg** 录制方案：

1. 通过 `Page.startScreencast` 从浏览器 compositor 拉取帧
2. 帧缓冲到内存，按时间戳排序
3. 通过 FFmpeg stdin 管道编码为 MP4/WebM

特点：
- **高帧率**：帧率由 compositor 决定，可达显示器刷新率（通常 60fps）
- **兼容性**：普通 Chromium/Edge 即可，无需特殊 Chrome 版本
- **高质量**：libx264 CRF 17 + preset slower
- **调试支持**：`save_frames_dir` 可保存原始帧
- **格式可选**：jpeg（有损，文件小）或 png（无损，画质最好）

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
```

### 命令行演示

```bash
# 录制模式（默认 msedge，60fps，1920x1080）
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --duration 10 --fps 60

# 使用 chromium + headless
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --browser chromium --headless

# PNG 无损录制（画质最好）
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --format png

# 自定义分辨率
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --width 1280 --height 720

# 保存原始帧用于调试
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --save-frames data/temp/frames

# 仅观察页面，不录制
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 \
    --no-record --duration 5

# JSON 输出模式（供父进程解析）
python -m webgal_agent.browser.demo record \
    --url http://localhost:3000 --json
```

### 命令行参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| `mode` | 必填 | `navigate` 或 `record` |
| `--url` | `https://example.com` | 目标 URL |
| `--output` | `data/temp/output.mp4` | 输出路径 |
| `--duration` | `5.0` | 录制时长（秒） |
| `--fps` | `60.0` | 输出帧率 |
| `--width` | `1920` | 视口宽度 |
| `--height` | `1080` | 视口高度 |
| `--selector` | `auto` | 录制目标 CSS 选择器，`auto` 自动检测 |
| `--browser` | `msedge` | 浏览器引擎：chromium / firefox / webkit / msedge |
| `--headless` | `False` | 无头模式 |
| `--no-record` | `False` | 跳过录制，仅等待观察 |
| `--screencast-quality` | `90` | Screencast JPEG 质量 (0-100) |
| `--format` | `jpeg` | 截图格式：jpeg / png |
| `--save-frames` | 无 | 保存原始帧到指定目录 |
| `--json` | `False` | JSON 输出模式（日志到 stderr，结果到 stdout） |

### 编程接口

```python
import asyncio
from webgal_agent.browser import (
    BrowserClient,
    DefaultBrowserConfig,
    ScreencastRecorder,
    Selector,
    SelectorType,
)
from webgal_agent.browser.models import VideoConfig


async def main():
    config = DefaultBrowserConfig(
        browser_type="msedge",
        headless=False,
        viewport_width=1920,
        viewport_height=1080,
        channel="msedge",
    )

    async with BrowserClient(config) as client:
        await client.new_context(context_id="default")

        # 注入脚本（在导航前）
        await client.add_script_injection(
            url_pattern="**/index-e1b3c40e.js",
            inject_code="window.changeScene = gCe;\nwindow.toggleAuto = wU;",
        )

        await client.navigate("http://localhost:3000", wait_until="load")

        # 录制
        video_cfg = VideoConfig(output_path="output.mp4", fps=60)
        recorder = ScreencastRecorder(client, video_cfg)
        result = await recorder.start(
            duration=10.0,
            format="jpeg",              # jpeg 或 png
            save_frames_dir=None,       # 可选：保存原始帧
        )

        print(f"录制完成: {result.total_frames} 帧, "
              f"源帧率 {result.source_fps:.1f} FPS, "
              f"输出帧率 {result.output_fps:.1f} FPS, "
              f"文件大小 {result.file_size_mb:.2f} MB")

asyncio.run(main())
```

### RecordingResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `output_path` | `Path` | 输出文件路径 |
| `total_frames` | `int` | 总帧数 |
| `duration` | `float` | 实际录制时长（秒） |
| `source_fps` | `float` | 源帧率（捕获的实际帧率） |
| `output_fps` | `float` | 输出帧率（ffmpeg 转换后的帧率） |
| `file_size_mb` | `float` | 文件大小（MB） |
| `actual_fps` | `float` | 向后兼容字段 |

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

## 选择器自动检测

`--selector auto` 模式按优先级检测可录制目标：

1. `#root` — WebGal 根元素
2. `canvas` — Canvas 元素

首个可见元素将被选为录制目标。未找到时继续录制整个页面。

## Windows 事件循环

在 Windows 上，Playwright 需要 `WindowsProactorEventLoopPolicy`。`demo.py` 在 `from webgal_agent.browser import ...` 之前设置此 policy。Web UI 录制通过独立子进程执行，自带独立 event loop，不受 FastAPI/Uvicorn 影响。
