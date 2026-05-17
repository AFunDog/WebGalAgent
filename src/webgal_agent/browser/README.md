# browser 模块

WebGalAgent 的浏览器自动化与录制子系统。

## 当前模块组成

```text
browser/
├── __init__.py
├── client.py
├── demo.py
├── models.py
├── screencast.py
├── tools.py
└── README.md
```

当前仓库里没有旧版 `recorder.py` 或 `capture.py` 文件，文档与实现应以这里的实际文件为准。

## 主要职责

- 启动和管理 Playwright 浏览器
- 页面导航、等待、点击、截图
- 拦截脚本并注入 WebGal 调试辅助代码
- 通过 CDP Screencast 录制页面
- 可选捕获 WebAudio 音频

## 关键组件

### `client.py`

`BrowserClient` 负责：

- `new_context()`
- `navigate()`
- `add_script_injection()`
- `create_cdp_session()`
- `wait_for()`
- `click()` / `fill()` / `get_text()`
- `prepare_time_control()`
- `prepare_webaudio_capture()`

### `demo.py`

命令行入口，支持：

- `navigate`
- `record`

也是当前 Web UI 录制能力的真实执行端。API 路由不会直接跑 Playwright，而是通过子进程调用这里。

### `screencast.py`

`ScreencastRecorder` 的当前实现：

1. `Page.startScreencast`
2. 收到的 JPEG/PNG 帧写入 `data/temp/webgal_screencast_*`
3. 可选抓取 PCM 音频并落地为 WAV
4. 录制结束后调用 FFmpeg 离线编码

这不是“实时管道编码到 ffmpeg stdin”的实现，文档不要再写旧架构。

## 当前录制流程

```text
demo.py
  -> BrowserClient.new_context()
  -> 可选 prepare_webaudio_capture()
  -> add_script_injection()
  -> navigate()
  -> 可选 WebGal scene/config 操作
  -> ScreencastRecorder.start()
       -> Page.startScreencast
       -> 帧写磁盘
       -> 可选音频增量拉取
       -> Page.stopScreencast
       -> ffmpeg 离线编码
```

## Web UI 与子进程隔离

`src/webgal_agent/api/routes/record.py` 通过子进程调用：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record --json ...
```

这样做的原因：

- Playwright 与 FastAPI/Uvicorn event loop 隔离
- 录制崩溃不会直接拖垮 API 进程
- stdout/stderr 可单独采集

## WebGal 相关注入规则

当前 `demo.py` 中录制 WebGal 页面时，会注入辅助符号，例如：

- `window.changeScene`
- `window.toggleAuto`
- `window.saveConfig`
- `window.loadConfig`
- `window.__webgal`
- `window.hideInfo`

### 配置注入结论

已确认的实现细节：

- IndexedDB 数据库名是 `localforage`
- 配置记录 key 当前按 `MyGO` 读取/写回
- `window.saveConfig()` 本身会触发异步数据库写入
- 如果紧跟着访问同一个 IndexedDB store，会与其内部异步写入发生冲突
- 因此 `saveConfig()` 后应先留一个短延迟，再执行自定义写入

这条规则比“脚本看起来是否同步”更重要。

## 命令示例

导航测试：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo navigate --url https://example.com
```

录制：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record `
  --url http://localhost:3001/games/MyGO3.0.0/ `
  --output data/temp/output.mp4 `
  --fps 60 --width 1920 --height 1080 `
  --format jpeg --record-audio
```

无固定时长，依赖停止条件：

```powershell
.\.venv\Scripts\python.exe -m webgal_agent.browser.demo record `
  --url http://localhost:3001/games/MyGO3.0.0/ `
  --duration 0 `
  --stop-on "window.__webgal.sceneManager.sceneData.currentScene.sceneUrl === './game/scene/start.txt'"
```

## 常用参数

| 参数 | 说明 |
|------|------|
| `--url` | 页面地址 |
| `--output` | 输出文件路径 |
| `--duration` | 最大录制时长；`0` 表示依赖 `--stop-on` |
| `--stop-on` | JS 表达式，truthy 时结束 |
| `--fps` | 输出帧率 |
| `--width` / `--height` | 视口大小 |
| `--selector` | `auto` 或指定 CSS |
| `--format` | `jpeg` / `png` |
| `--record-audio` | 开启音频捕获 |
| `--game-config` | 注入游戏配置 JSON |
| `--json` | 机器可读输出模式 |

## Windows 注意事项

在 Windows 上，`demo.py` 必须在导入 Playwright 之前设置：

```python
asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

不要把这个设置挪到 `client.py`、`screencast.py` 或 API 业务层。

## 当前文档约束

更新 browser 文档时，必须与以下事实保持一致：

- 当前录制器是 `ScreencastRecorder`
- 当前帧缓存策略是“写临时目录后离线编码”
- 当前 API 录制模式是“子进程调用 demo CLI”
- 当前 WebGal 配置注入依赖 `saveConfig()` 后短延迟
