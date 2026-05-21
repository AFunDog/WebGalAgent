# 浏览器录制链路细节

最后更新: 2026-05-21

## 主链路

1. `/api/record/start` 接收前端录制配置。
2. `src/webgal_agent/api/routes/record.py` 组装 CLI 参数并启动子进程。
3. 子进程执行 `python -m webgal_agent.browser.demo record --json`。
4. `demo_session.py` 完成导航、元素等待、WebGal 专属准备。
5. `ScreencastRecorder` 通过 `Page.startScreencast` 抓帧。
6. 帧先落到 `data/browser/temp/`，结束后由 FFmpeg 离线编码。
7. `stdout` 最后一行 JSON 作为最终结果返回给 API，`stderr` 作为实时日志。

## 代码位置

- API 协调：`src/webgal_agent/api/routes/record.py`
- CLI 入口：`src/webgal_agent/browser/demo.py`
- 参数解析：`src/webgal_agent/browser/demo_cli.py`
- 录制会话：`src/webgal_agent/browser/demo_session.py`
- 录制器：`src/webgal_agent/browser/screencast.py`
- 音频抓取：`src/webgal_agent/browser/audio_capture.py`
- 编码：`src/webgal_agent/browser/ffmpeg_encoder.py`

## 模式分歧

`page_mode=webgal`：

- 等待 WebGal 辅助符号
- 可选切场景
- 可选注入配置
- 录制前执行自动播放与 UI 隐藏

`page_mode=generic`：

- 不执行任何 WebGal 专属准备
- 只做通用导航、元素等待和录制

## 当前约束

- `--duration 0` 必须搭配 `--stop-on`
- CLI 的 `--selector auto` 规则是 `#root -> canvas`
- 录制页默认选择器最终以 `src/configs/record.yaml` 为准
- `saveConfig()` 后必须短延迟，再访问同一 IndexedDB store
- API 子进程模式是当前稳定边界，不应在文档里写成“FastAPI 内嵌 Playwright”
