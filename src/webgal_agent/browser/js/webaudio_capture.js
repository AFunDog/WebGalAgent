(() => {
    const NativeAudioContext = window.AudioContext || window.webkitAudioContext;
    if (!NativeAudioContext) return;

    const contexts = new Set();
    let _originalConnect = null;

    function setupMasterGain(ctx) {
        if (ctx.__masterGain__) return;

        const masterGain = ctx.createGain();
        const mediaDest = ctx.createMediaStreamDestination();
        const connectFn = _originalConnect || AudioNode.prototype.connect;

        connectFn.call(masterGain, ctx.destination);
        connectFn.call(masterGain, mediaDest);

        const osc = ctx.createOscillator();
        const silentGain = ctx.createGain();
        silentGain.gain.value = 0;
        osc.connect(silentGain);
        connectFn.call(silentGain, masterGain);
        osc.start();

        ctx.__masterGain__ = masterGain;
        ctx.__mediaStreamDest__ = mediaDest;

        if (ctx.state === "suspended") {
            ctx.resume();
        }
    }

    function patchConnect() {
        if (_originalConnect) return;
        _originalConnect = AudioNode.prototype.connect;

        AudioNode.prototype.connect = function (...args) {
            const target = args[0];
            const ctx = this.context;
            const result = _originalConnect.apply(this, args);

            if (
                ctx &&
                ctx.__masterGain__ &&
                this !== ctx.__masterGain__ &&
                target !== ctx.__masterGain__
            ) {
                try {
                    _originalConnect.call(this, ctx.__masterGain__);
                } catch (e) {}
            }
            return result;
        };
    }

    function patchContext(ctx) {
        if (ctx.__patched_for_capture__) return;
        ctx.__patched_for_capture__ = true;
        patchConnect();
        setupMasterGain(ctx);
    }

    const OriginalAC = NativeAudioContext;

    window.AudioContext = function (...args) {
        const ctx = new OriginalAC(...args);
        contexts.add(ctx);
        patchContext(ctx);
        return ctx;
    };
    window.AudioContext.prototype = OriginalAC.prototype;
    if (window.webkitAudioContext) {
        window.webkitAudioContext = window.AudioContext;
    }
    patchConnect();

    window.__getCapturedStream = () => {
        const tracks = [];
        for (const ctx of contexts) {
            const stream = ctx.__mediaStreamDest__?.stream;
            if (!stream) continue;
            for (const track of stream.getAudioTracks()) {
                tracks.push(track);
            }
        }
        return new MediaStream(tracks);
    };

    window.__startTrackProcessor = () => {
        if (window.__trackProcessorStarted) return true;
        if (!window.MediaStreamTrackProcessor) {
            console.warn("[WebAudio Capture] MediaStreamTrackProcessor unavailable");
            return false;
        }

        const stream = window.__getCapturedStream();
        const track = stream.getAudioTracks()[0];
        if (!track) return false;

        const processor = new MediaStreamTrackProcessor({ track });
        const reader = processor.readable.getReader();

        const settings = track.getSettings();
        window.__audioPcmMeta = {
            sampleRate: settings.sampleRate || 48000,
            channels: settings.channelCount || 2,
        };
        window.__audioPcmChunks = [];

        (async () => {
            try {
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    const nFrames = value.numberOfFrames;
                    const nChannels = value.numberOfChannels;
                    const interleaved = new Float32Array(nFrames * nChannels);

                    for (let ch = 0; ch < nChannels; ch++) {
                        const plane = new Float32Array(nFrames);
                        value.copyTo(plane, { planeIndex: ch });
                        for (let i = 0; i < nFrames; i++) {
                            interleaved[i * nChannels + ch] = plane[i];
                        }
                    }

                    window.__audioPcmChunks.push(interleaved);
                    value.close();
                }
            } catch (e) {
                console.warn("[WebAudio Capture] reader loop ended:", e.message);
            }
        })();

        window.__trackProcessorStarted = true;
        console.log(
            "[WebAudio Capture] TrackProcessor started, " +
                window.__audioPcmMeta.sampleRate +
                "Hz " +
                window.__audioPcmMeta.channels +
                "ch",
        );
        return true;
    };

    function getOrCreateCaptureCtx() {
        for (const ctx of contexts) {
            if (ctx.state === "running" || ctx.state === "suspended") {
                return ctx;
            }
        }
        return new AudioContext();
    }

    const _origPlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (...args) {
        if (!this.__webAudioRouted) {
            this.__webAudioRouted = true;
            try {
                const ctx = getOrCreateCaptureCtx();
                const src = ctx.createMediaElementSource(this);
                const connectFn = _originalConnect || AudioNode.prototype.connect;
                connectFn.call(src, ctx.__masterGain__ || ctx.destination);
                this.__srcNode = src;
                console.log("[WebAudio Capture] routed <audio> to masterGain");
            } catch (e) {
                console.log("[WebAudio Capture] <audio> already in WebAudio graph");
            }
        }
        return _origPlay.apply(this, args);
    };

    window.__checkAudioSignal = () => {
        const chunks = window.__audioPcmChunks;
        if (!chunks || chunks.length === 0) {
            const ctxStates = [];
            for (const ctx of contexts) {
                ctxStates.push(ctx.state);
            }
            return {
                status: "no_data",
                audioContextStates: ctxStates,
                routedAudioElements: document.querySelectorAll("audio").length,
            };
        }

        let maxAbs = 0;
        let sumAbs = 0;
        let count = 0;
        for (const c of chunks) {
            for (let i = 0; i < c.length; i++) {
                const abs = Math.abs(c[i]);
                sumAbs += abs;
                if (abs > maxAbs) maxAbs = abs;
                count++;
            }
        }

        const ctxStates = [];
        for (const ctx of contexts) {
            ctxStates.push(ctx.state);
        }

        return {
            status: maxAbs > 1e-6 ? "signal_detected" : "silent",
            maxAmplitude: maxAbs,
            meanAmplitude: count > 0 ? sumAbs / count : 0,
            sampleCount: count,
            audioContextStates: ctxStates,
            routedAudioElements: document.querySelectorAll("audio").length,
        };
    };

    function ensureSyncOverlay() {
        let overlay = document.getElementById("__av-sync-debug-overlay");
        if (overlay) return overlay;

        overlay = document.createElement("div");
        overlay.id = "__av-sync-debug-overlay";
        overlay.style.position = "fixed";
        overlay.style.inset = "0";
        overlay.style.background = "#ff0000";
        overlay.style.opacity = "0";
        overlay.style.pointerEvents = "none";
        overlay.style.zIndex = "2147483647";
        overlay.style.transition = "none";
        document.documentElement.appendChild(overlay);
        return overlay;
    }

    window.__stopAvSyncDebug = () => {
        const state = window.__avSyncDebugState;
        if (!state) return false;

        state.stopped = true;
        if (state.timerId) {
            clearTimeout(state.timerId);
        }
        if (state.overlay) {
            state.overlay.style.opacity = "0";
        }
        window.__avSyncDebugState = null;
        return true;
    };

    window.__startAvSyncDebug = async (opts = {}) => {
        window.__stopAvSyncDebug();

        const intervalMs = Math.max(Number(opts.intervalMs) || 0, 100);
        if (!intervalMs) {
            return { ok: false, reason: "interval_disabled" };
        }

        const flashMs = Math.max(Number(opts.flashMs) || 120, 10);
        const toneMs = Math.max(Number(opts.toneMs) || 120, 10);
        const frequency = Math.max(Number(opts.frequency) || 880, 1);
        const gainValue = Math.min(Math.max(Number(opts.gain) || 0.25, 0.01), 1.0);
        const initialDelayMs = Math.max(
            Number(opts.initialDelayMs) || Math.min(intervalMs, 1000),
            0,
        );

        const ctx = getOrCreateCaptureCtx();
        patchContext(ctx);
        if (ctx.state === "suspended") {
            await ctx.resume();
        }

        const overlay = ensureSyncOverlay();
        const connectFn = _originalConnect || AudioNode.prototype.connect;

        const state = {
            stopped: false,
            timerId: null,
            overlay,
            intervalMs,
        };
        window.__avSyncDebugState = state;

        const firePulse = () => {
            if (state.stopped) return;

            requestAnimationFrame(() => {
                if (state.stopped) return;

                overlay.style.opacity = "1";
                setTimeout(() => {
                    if (!state.stopped) {
                        overlay.style.opacity = "0";
                    }
                }, flashMs);

                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = "square";
                osc.frequency.setValueAtTime(frequency, ctx.currentTime);

                gain.gain.setValueAtTime(0, ctx.currentTime);
                gain.gain.linearRampToValueAtTime(gainValue, ctx.currentTime + 0.002);
                gain.gain.setValueAtTime(
                    gainValue,
                    ctx.currentTime + Math.max(toneMs / 1000 - 0.004, 0.002),
                );
                gain.gain.linearRampToValueAtTime(0, ctx.currentTime + toneMs / 1000);

                osc.connect(gain);
                connectFn.call(gain, ctx.__masterGain__ || ctx.destination);
                osc.start(ctx.currentTime);
                osc.stop(ctx.currentTime + toneMs / 1000 + 0.01);
            });

            state.timerId = setTimeout(firePulse, intervalMs);
        };

        state.timerId = setTimeout(firePulse, initialDelayMs);
        return {
            ok: true,
            intervalMs,
            flashMs,
            toneMs,
            frequency,
            initialDelayMs,
        };
    };

    console.log("[WebAudio Capture] graph + HTMLAudio hook installed");
})();
