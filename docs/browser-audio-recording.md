# 浏览器录制模块 — 音频录制缺失

## 现状

当前的 CDP Screencast 录制器只捕获视频帧（`Page.startScreencast`），不录制音频。ffmpeg 编码时带了 `-an`（no audio）标志，输出视频为无声文件。

## 根因

`Page.startScreencast` 是 Chrome DevTools 的截图接口，只输出 compositor 的 JPEG/PNG 帧，不包含任何音频数据。CDP 没有等价的"音频流"接口。

## 可选方案

### 方案 1：CDP 音频捕获 + 合成

通过 CDP 的 `Tracing` 或 `Media` 域获取音频，或直接用 Playwright 的 `page.route()` 拦截音频资源下载到本地。录制结束时用 ffmpeg 将音频与视频混流。

### 方案 2：Windows 系统音频回环

用 ffmpeg 的 WASAPI 回环设备或 Stereo Mix 独立录制系统音频，最后与视频时间轴对齐混流。

### 方案 3：playwright-video 插件

部分第三方 Playwright 视频录制插件使用 CanvasCaptureStream + MediaRecorder 或 WebCodecs 同时捕获画布和音频，但帧率和质量不如 CDP Screencast。

### 方案 4：OBS / FFmpeg 独立音频录制

单独启动 ffmpeg 进程录制系统音频（WASAPI loopback 或 Stereo Mix），记录开始时间戳，结束后与视频混流。

## 推荐方向

方案 2 或方案 4：用 ffmpeg 的 `-f dshow` 或 `-f avfoundation`（macOS）独立录制音频，在编码阶段将视频帧序列与音频轨道用 `-shortest` 混流。这样可以保持视频录制链路的独立性，音频故障不影响视频产出。

## 当前临时方案

视频录制正常，FFmpeg 命令中带 `-an` 标志跳过了音频轨道。
