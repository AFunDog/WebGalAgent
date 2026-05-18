# 浏览器录制流程说明

最后更新: 2026-05-18

本文档只描述当前仓库真实录制行为，不保留旧实现。

## 当前录制链路

1. API 路由 `src/webgal_agent/api/routes/record.py` 启动子进程。
2. 子进程执行 `src/webgal_agent/browser/demo.py` 的 `record` 模式。
3. `demo.py` 在导航前注入 WebAudio 捕获和 WebGal 页面辅助脚本。
4. 页面加载完成后等待 `changeScene` 等辅助符号就绪。
5. 切换场景，可选注入 IndexedDB 游戏配置。
6. 调用 `toggleAuto()` 和 `hideInfo()` 完成录制前准备。
7. `ScreencastRecorder` 启动 `Page.startScreencast`，把帧落到 `data/temp/`。
8. 录制结束后离线调用 FFmpeg 生成 `.mp4` 或 `.webm`。

## 关键约束

- `--duration 0` 只有配合 `--stop-on` 才有意义。
- `selector=auto` 先查找 `#root`，失败后回退到 `canvas`。
- `saveConfig()` 会触发页面自身的异步 IndexedDB 写入。
- 因此自定义配置写回前必须留短延迟，避免同 store 冲突。
- API 只把 CLI 当作子进程，不直接持有 Playwright 对象。

## 当前代码位置

- CLI 入口: `src/webgal_agent/browser/demo.py`
- CLI 参数与模式分发: `src/webgal_agent/browser/demo_cli.py`
- 录制会话实现: `src/webgal_agent/browser/demo_session.py`
- 注入脚本常量: `src/webgal_agent/browser/webgal_injection.py`
- 录制器: `src/webgal_agent/browser/screencast.py`
- 音频抓取: `src/webgal_agent/browser/audio_capture.py`
- 编码辅助: `src/webgal_agent/browser/ffmpeg_encoder.py`
- API 子进程协调: `src/webgal_agent/api/routes/record.py`

## 当前输出协议

- CLI `--json` 模式下，日志写到 `stderr`。
- 最终结果只在 `stdout` 输出一行 JSON。
- API 层读取 `stderr` 作为实时日志，读取 `stdout` 最后一行作为最终结果。
