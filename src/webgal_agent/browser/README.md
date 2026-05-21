# browser 模块

当前 `browser/` 目录承载 WebGalAgent 的浏览器自动化与录制专题。它既服务 CLI，也服务 Web UI 的 `/record` 页面。

## 模块边界

这个目录负责：

- 启动与管理 Playwright 浏览器
- 页面导航、元素等待、CDP 会话创建
- WebGal 页面辅助注入
- WebAudio 音频抓取
- Screencast 帧采集与 FFmpeg 离线编码

这个目录不负责：

- FastAPI 路由协议定义
- 前端表单状态管理
- 任务流水线编排

## 当前文件职责

```text
browser/
├── client.py             # 浏览器上下文、页面操作、CDP 会话
├── demo.py               # CLI 入口；Windows event loop policy 在这里设定
├── demo_cli.py           # 参数解析、json/log 输出协议
├── demo_session.py       # navigate / record 两类会话实现
├── screencast.py         # ScreencastRecorder
├── audio_capture.py      # WebAudio PCM 抓取与 WAV 落盘
├── ffmpeg_encoder.py     # 帧目录 -> 视频编码/合流
├── webgal_injection.py   # WebGal 页面辅助注入脚本
├── webgal_session.py     # WebGal 页面专属准备逻辑
├── script_loader.py      # 加载独立 JS 资源
└── js/webaudio_capture.js
```

## 当前录制架构

真实链路如下：

```text
/record 页面 或 手工 CLI
  -> /api/record/start
  -> 子进程: python -m webgal_agent.browser.demo record --json
  -> demo_session.demo_record()
  -> ScreencastRecorder.start()
  -> Page.startScreencast 抓帧到 data/browser/temp/
  -> ffmpeg 离线编码
  -> stdout 返回最终 JSON，stderr 输出过程日志
```

关键事实：

- API 只是子进程协调层，不直接持有 Playwright 对象
- 当前默认录制器是 `ScreencastRecorder`
- 当前默认模式是“临时帧目录 + 事后编码”，不是“实时推流进 ffmpeg stdin”
- 音频抓取是可选项，走 WebAudio hook + PCM/WAV 合流

## CLI 入口与默认值

CLI 入口：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record
```

CLI 自身的关键默认值：

- `--selector auto`
- `--page-mode webgal`
- `--browser msedge`
- `--fps 60`

其中 `auto` 的规则是：

1. 先尝试 `#root`
2. 找不到再回退到 `canvas`

注意：Web UI 录制页会先从 `/api/record/config` 读取 `src/configs/record.yaml`，因此页面表单的默认选择器以配置文件为准，不一定等于 CLI 的 `auto` 默认值。当前 `record.yaml` 默认是具体 CSS 选择器 `div._MainStage_main_9enex_1`。

## WebGal 页面专属规则

`page_mode=webgal` 时，会执行以下准备逻辑：

- 注入 `changeScene`、`toggleAuto`、`hideInfo`、`saveConfig`、`loadConfig` 等辅助入口
- 等待页面辅助符号就绪
- 可选切换场景
- 可选通过 IndexedDB 注入游戏配置
- 录制前隐藏 UI、开启自动播放

`page_mode=generic` 时，上述 WebGal 专属逻辑全部跳过，只保留通用导航、等待和录制。

## 配置注入规则

当前确认的约束：

- IndexedDB 数据库名是 `localforage`
- 录制配置覆盖当前按 key `MyGO` 读写
- `window.saveConfig()` 会触发异步 IndexedDB 写入
- 调用 `saveConfig()` 后不能立即访问同一 store
- 需要保留一个短延迟，再执行自定义写回

这条规则是实现约束，不是可选优化。

## 录制参数边界

常用参数：

| 参数 | 说明 |
|------|------|
| `--url` | 页面地址 |
| `--output` | 输出文件 |
| `--duration` | 最大录制时长 |
| `--stop-on` | JS 停止条件 |
| `--selector` | `auto` 或指定 CSS |
| `--page-mode` | `webgal` / `generic` |
| `--browser` | `chromium` / `msedge` / `firefox` / `webkit` |
| `--record-audio` | 捕获页面音频 |
| `--save-logs` | 把运行日志写到输出文件旁边 |
| `--game-config` | JSON 形式的 IndexedDB 覆盖 |

参数约束：

- `--duration 0` 只有在同时提供 `--stop-on` 时才有效
- PowerShell 里传 `#root` 需要写成 `--selector '#root'`
- `--json` 模式下，日志走 `stderr`，最终结果 JSON 走 `stdout`

## 常用命令

导航：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo navigate --url https://example.com
```

录制 WebGal 页面：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record `
  --url http://localhost:3001/games/MyGO3.0.0/ `
  --output data/browser/recordings/output.mp4 `
  --fps 60 --width 1920 --height 1080 `
  --record-audio --save-logs
```

录制通用页面：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record `
  --url https://example.com `
  --page-mode generic `
  --selector auto `
  --output data/browser/recordings/output.mp4
```

停止条件驱动录制：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record `
  --url http://localhost:3001/games/MyGO3.0.0/ `
  --duration 0 `
  --stop-on "window.__webgal.sceneManager.sceneData.currentScene.sceneUrl === './game/scene/start.txt'"
```

## Windows 注意事项

Windows 上需要在入口点先设置：

```python
asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

当前允许设置的位置：

- `src/webgal_agent/__main__.py`
- `src/webgal_agent/browser/demo.py`

不要把它挪到 `client.py`、`screencast.py` 或 API 业务模块。
