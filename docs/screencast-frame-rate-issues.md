# CDP Screencast 帧率问题分析

## 现象

录制输出视频如"慢放"，实际帧率达不到目标帧率。

日志证据：

```
[ScreencastRecorder] 源帧率: 47.52 FPS
[ScreencastRecorder] 源帧率: 47.52 FPS → 输出帧率: 60 FPS
实际录制时长: 447.69s
捕获帧数: 21274
```

21274 / 447.69 ≈ 47.52 FPS — 源帧率只有 47.52，却强行要求 ffmpeg 输出 60fps。

## 根因

### 1. CDP Screencast 不是高性能录制接口

`Page.startScreencast` 是 Chrome DevTools 的调试接口，设计目标不是 60fps 实时视频采集。每帧链路：

```
Chrome GPU → JPEG 编码 → Base64 → CDP WebSocket → Playwright → Python → Base64 解码 → 写管道 → ffmpeg → x264 编码
```

1920×1080×60fps = 每秒 124M 像素，JPEG quality=95 数据量巨大，Python 单线程处理不过来。

### 2. CDP Screencast 是 VFR（可变帧率）

Chrome 在页面无变化、CPU/GPU 繁忙、WebSocket 堵塞时都会掉帧，帧间隔不均匀。

### 3. CFR/VFR 时间戳错位

源 VFR 帧被当作 CFR 喂给 ffmpeg，`-framerate` 告诉 ffmpeg 每帧间隔固定，但实际间隔不均匀。时间轴错位导致视频像慢放。

### 4. 实时编码反向阻塞

ffmpeg 一边收帧一边编码（JPEG decode → colorspace → x264 → mp4 mux），编码慢会阻塞 CDP 帧接收，进一步掉帧。

### 5. quality=95 过重

JPEG 95 和 80 肉眼差别很小，但编码/传输/解码开销大很多。

### 6. ffmpeg preset 默认 medium

1080p60 x264 medium preset 实时编码负担重。

## 修复方案

### 方案 1：用实际帧率作为输出帧率 ✅ 已实现

`output_fps` 不应强制 60，而是用实际录到的帧率：

```python
output_fps = int(round(source_fps))  # 如 48
```

已实现在 `screencast.py` 的 `start()` 方法中。

### 方案 2：先存帧再编码 ✅ 已实现

录制阶段帧直接 `write_bytes` 到临时目录（`tempfile.mkdtemp`），零编码开销。录制结束后用 ffmpeg 批量编码（`_encode_from_dir`）。

流程：
```text
录制时: CDP 帧 → Base64 解码 → 写磁盘 (frame_00000001.jpg)
结束后: ffmpeg -framerate <fps> -i frame_%08d.jpg -r <output_fps> ...
```

已实现在 `screencast.py` 中，替代了旧的实时管道编码（`_encode` 方法已删除）。

### 方案 3：降低质量参数

```bash
--screencast-quality 80  # 95 → 80，肉眼无差，性能提升明显
```

### 方案 4：ffmpeg 用 ultrafast preset ✅ 已实现

当前默认 `-preset ultrafast`（mp4）/ `-deadline good -cpu-used 2`（webm）。

### 方案 5：降低目标帧率

WebGAL 不是高动态内容，30fps 足够：

```bash
--fps 30
```

### 方案 6：时间轴驱动而非帧驱动

不用 `timestamp = frame_index / fps`，用真实时间戳：

```python
timestamp = now - start_time
```

> 已通过方案 1+2 间接解决：帧保存时不分配时间戳，ffmpeg 按 `-framerate <source_fps>` 统一分配 PTS。

### 方案 7：不用 CDP Screencast（如果真的需要稳定 60fps）

替代方案：OBS、GPU Capture、Windows Graphics Capture、ffmpeg gdigrab/dxgi、WebCodecs + CanvasCaptureStream、MediaRecorder。

## 日志标记

此问题在 `ScreencastRecorder` 日志中表现为：

```
[ScreencastRecorder] 源帧率: X FPS → 输出帧率: 60 FPS
```

当 source_fps 明显低于 output_fps 时，视频就会出现慢放/卡顿。
