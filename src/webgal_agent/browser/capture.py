"""CCapture.js 驱动的目标元素录制。"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

from webgal_agent.browser.models import CaptureConfig

_ASSETS_DIR = Path(__file__).with_name("assets")
_CCAPTURE_ASSET = _ASSETS_DIR / "CCapture.all.min.js"
_HTML2CANVAS_ASSET = _ASSETS_DIR / "html2canvas.min.js"

_CCAPTURE_BRIDGE_SCRIPT = """
() => {
    if (window.__webgalCCaptureBridgeReady) {
        return;
    }

    window.__webgalCCaptureBridge = {
        capturer: null,
        mirrorCanvas: null,
        overlayCanvas: null,
        overlayDirty: true,
        overlayObserver: null,
        overlaySelector: null,
        selector: "canvas",
        fps: 30,
        totalFrames: 0,
        width: 0,
        height: 0,

        ensureMirrorCanvas(width, height) {
            const nextWidth = Math.max(1, Math.ceil(width));
            const nextHeight = Math.max(1, Math.ceil(height));

            if (!this.mirrorCanvas) {
                const canvas = document.createElement("canvas");
                canvas.setAttribute("data-webgal-agent-capture", "true");
                canvas.style.position = "fixed";
                canvas.style.left = "-100000px";
                canvas.style.top = "-100000px";
                canvas.style.pointerEvents = "none";
                canvas.style.opacity = "0";
                document.body.appendChild(canvas);
                this.mirrorCanvas = canvas;
            }

            if (this.mirrorCanvas.width !== nextWidth) {
                this.mirrorCanvas.width = nextWidth;
            }
            if (this.mirrorCanvas.height !== nextHeight) {
                this.mirrorCanvas.height = nextHeight;
            }
            return this.mirrorCanvas;
        },

        ensureOverlayCanvas(width, height) {
            const nextWidth = Math.max(1, Math.ceil(width));
            const nextHeight = Math.max(1, Math.ceil(height));

            if (!this.overlayCanvas) {
                const canvas = document.createElement("canvas");
                canvas.setAttribute("data-webgal-agent-overlay-capture", "true");
                canvas.style.position = "fixed";
                canvas.style.left = "-100000px";
                canvas.style.top = "-100000px";
                canvas.style.pointerEvents = "none";
                canvas.style.opacity = "0";
                document.body.appendChild(canvas);
                this.overlayCanvas = canvas;
            }

            if (this.overlayCanvas.width !== nextWidth) {
                this.overlayCanvas.width = nextWidth;
            }
            if (this.overlayCanvas.height !== nextHeight) {
                this.overlayCanvas.height = nextHeight;
            }
            return this.overlayCanvas;
        },

        findTarget(selector) {
            return document.querySelector(selector);
        },

        disconnectOverlayObserver() {
            if (this.overlayObserver) {
                this.overlayObserver.disconnect();
                this.overlayObserver = null;
            }
        },

        watchOverlayChanges(target) {
            if (this.overlaySelector === this.selector && this.overlayObserver) {
                return;
            }

            this.disconnectOverlayObserver();
            this.overlaySelector = this.selector;
            this.overlayDirty = true;

            this.overlayObserver = new MutationObserver(() => {
                this.overlayDirty = true;
            });
            this.overlayObserver.observe(target, {
                attributes: true,
                characterData: true,
                childList: true,
                subtree: true,
            });
        },

        async renderOverlay(target, rect) {
            const overlayCanvas = this.ensureOverlayCanvas(rect.width, rect.height);
            const overlayCtx = overlayCanvas.getContext("2d");
            overlayCtx.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);

            await window.html2canvas(target, {
                backgroundColor: null,
                canvas: overlayCanvas,
                ignoreElements: (element) => {
                    if (element instanceof HTMLCanvasElement) {
                        return true;
                    }
                    if (element instanceof HTMLVideoElement) {
                        return true;
                    }
                    if (element.hasAttribute?.("data-webgal-agent-capture")) {
                        return true;
                    }
                    if (element.hasAttribute?.("data-webgal-agent-overlay-capture")) {
                        return true;
                    }
                    return false;
                },
                logging: false,
                scale: 1,
                useCORS: true,
                width: Math.ceil(rect.width),
                height: Math.ceil(rect.height),
            });
            this.overlayDirty = false;
            return overlayCanvas;
        },

        drawVisualElement(ctx, element, rootRect) {
            const rect = element.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) {
                return false;
            }

            const dx = rect.left - rootRect.left;
            const dy = rect.top - rootRect.top;

            try {
                ctx.drawImage(element, dx, dy, rect.width, rect.height);
                return true;
            } catch (error) {
                console.warn("Failed to draw visual element", error);
                return false;
            }
        },

        async snapshotTarget(selector) {
            const target = this.findTarget(selector);
            if (!target) {
                throw new Error(`Target element not found: ${selector}`);
            }

            if (target instanceof HTMLCanvasElement) {
                return {
                    canvas: target,
                    width: target.width || target.clientWidth,
                    height: target.height || target.clientHeight,
                    tagName: "CANVAS",
                };
            }

            const rect = target.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) {
                throw new Error(`Target element has invalid size: ${selector}`);
            }

            const canvas = this.ensureMirrorCanvas(rect.width, rect.height);
            const ctx = canvas.getContext("2d");
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            this.watchOverlayChanges(target);

            const visualElements = [
                ...Array.from(target.querySelectorAll("canvas")),
                ...Array.from(target.querySelectorAll("video")).filter(
                    (video) => video.readyState >= 2,
                ),
            ];
            for (const element of visualElements) {
                this.drawVisualElement(ctx, element, rect);
            }

            const overlayCanvas = this.overlayDirty
                ? await this.renderOverlay(target, rect)
                : this.ensureOverlayCanvas(rect.width, rect.height);
            ctx.drawImage(overlayCanvas, 0, 0);

            return {
                canvas,
                width: canvas.width,
                height: canvas.height,
                tagName: target.tagName,
            };
        },

        async start(options) {
            this.selector = options.selector;
            this.fps = options.fps;
            this.totalFrames = 0;

            const snapshot = await this.snapshotTarget(this.selector);
            this.width = snapshot.width;
            this.height = snapshot.height;

            this.capturer = new window.CCapture({
                display: false,
                format: "webm",
                framerate: this.fps,
                name: options.name || "webgal-agent-capture",
                quality: options.quality ?? 100,
                verbose: false,
            });
            this.capturer.start();
        },

        async captureFrame() {
            if (!this.capturer) {
                throw new Error("CCapture has not been started");
            }

            const target = this.findTarget(this.selector);
            if (!target) {
                throw new Error(`Target element not found: ${this.selector}`);
            }

            const snapshot = await this.snapshotTarget(this.selector);
            this.width = snapshot.width;
            this.height = snapshot.height;
            this.capturer.capture(snapshot.canvas);
            this.totalFrames += 1;

            return {
                frameIndex: this.totalFrames - 1,
                height: this.height,
                ok: true,
                width: this.width,
            };
        },

        async stop() {
            if (!this.capturer) {
                throw new Error("CCapture has not been started");
            }

            const capturer = this.capturer;
            this.capturer = null;
            this.disconnectOverlayObserver();
            capturer.stop();

            const result = await new Promise((resolve, reject) => {
                try {
                    capturer.save((blob) => {
                        const reader = new FileReader();
                        reader.onerror = () => reject(new Error("Failed to read CCapture blob"));
                        reader.onloadend = () => {
                            resolve({
                                dataUrl: reader.result,
                                frameCount: this.totalFrames,
                                height: this.height,
                                mimeType: blob.type || "video/webm",
                                size: blob.size || 0,
                                width: this.width,
                            });
                        };
                        reader.readAsDataURL(blob);
                    });
                } catch (error) {
                    reject(error);
                }
            });

            return result;
        },
    };

    window.__webgalCCaptureBridgeReady = true;
}
"""


@dataclass
class Frame:
    """兼容旧接口保留的帧结构。"""

    data: bytes
    timestamp: float
    frame_index: int


@dataclass
class CaptureStats:
    """捕获统计。"""

    total_frames: int = 0
    dropped_frames: int = 0
    elapsed_time: float = 0.0
    actual_fps: float = 0.0


@dataclass
class CaptureArtifact:
    """浏览器端产物。"""

    data: bytes
    frame_count: int
    width: int
    height: int
    mime_type: str


class CanvasCapture:
    """基于 CCapture.js 的目标元素捕获器。"""

    def __init__(
        self,
        page,
        config: CaptureConfig | None = None,
        enable_time_control: bool = False,
        advance_frame_fn=None,
    ) -> None:
        self._page = page
        self._config = config or CaptureConfig()
        self._enable_time_control = enable_time_control
        self._advance_frame = advance_frame_fn
        self._stats = CaptureStats()
        self._running = False

    @property
    def stats(self) -> CaptureStats:
        return self._stats

    async def _ensure_runtime(self) -> None:
        ready = await self._page.evaluate("() => !!window.__webgalCCaptureBridgeReady")
        if ready:
            return

        await self._page.add_script_tag(path=str(_CCAPTURE_ASSET.resolve()))
        await self._page.add_script_tag(path=str(_HTML2CANVAS_ASSET.resolve()))
        await self._page.evaluate(_CCAPTURE_BRIDGE_SCRIPT)

    async def start(self) -> CaptureArtifact:
        """执行完整捕获并返回浏览器端产物。"""
        await self._ensure_runtime()

        if self._config.max_frames is not None:
            total_frames = self._config.max_frames
        elif self._config.max_duration is not None:
            total_frames = max(1, int(round(self._config.max_duration * self._config.fps)))
        else:
            total_frames = 1

        await self._page.evaluate(
            """async ({ fps, name, quality, selector }) => {
                await window.__webgalCCaptureBridge.start({
                    fps,
                    name,
                    quality,
                    selector,
                });
            }""",
            {
                "fps": self._config.fps,
                "name": "webgal-agent-capture",
                "quality": 100,
                "selector": self._config.canvas_selector,
            },
        )

        self._running = True
        dropped_frames = 0
        try:
            for _ in range(total_frames):
                try:
                    await self._page.evaluate(
                        "() => window.__webgalCCaptureBridge.captureFrame()"
                    )
                except Exception:
                    dropped_frames += 1
        finally:
            self._running = False

        result = await self._page.evaluate(
            "() => window.__webgalCCaptureBridge.stop()"
        )
        if not isinstance(result, dict):
            raise RuntimeError("CCapture did not return a valid artifact")

        data_url = str(result["dataUrl"])
        _, encoded = data_url.split(",", 1)
        artifact = CaptureArtifact(
            data=base64.b64decode(encoded),
            frame_count=int(result["frameCount"]),
            width=int(result["width"]),
            height=int(result["height"]),
            mime_type=str(result["mimeType"]),
        )

        self._stats = CaptureStats(
            total_frames=artifact.frame_count,
            dropped_frames=dropped_frames,
            elapsed_time=artifact.frame_count / self._config.fps if artifact.frame_count else 0.0,
            actual_fps=self._config.fps if artifact.frame_count else 0.0,
        )
        return artifact

    def stop(self) -> None:
        """保留兼容接口。"""
        self._running = False
