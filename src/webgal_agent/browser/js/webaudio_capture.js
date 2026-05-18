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

    console.log("[WebAudio Capture] graph + HTMLAudio hook installed");
})();
