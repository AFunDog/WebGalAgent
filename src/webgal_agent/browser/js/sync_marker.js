({ flashMs = 200, beepMs = 120, frequency = 1000 } = {}) => {
    const markerId = "__sync_marker__";
    const existing = document.getElementById(markerId);
    if (existing) existing.remove();

    const marker = document.createElement("div");
    marker.id = markerId;
    marker.style.position = "fixed";
    marker.style.left = "0";
    marker.style.top = "0";
    marker.style.width = "140px";
    marker.style.height = "140px";
    marker.style.background = "#ff2d55";
    marker.style.boxShadow = "0 0 0 99999px rgba(255,255,255,0.82)";
    marker.style.pointerEvents = "none";
    marker.style.zIndex = "2147483647";
    document.body.appendChild(marker);
    setTimeout(() => marker.remove(), flashMs);

    const perfNowMs = performance.now();
    const wallClockMs = Date.now();
    let audioScheduled = false;
    let audioError = null;

    try {
        const AC = window.AudioContext || window.webkitAudioContext;
        if (AC) {
            const ctx = new AC();
            if (ctx.state === "suspended") {
                void ctx.resume();
            }
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            gain.gain.value = 0.18;
            osc.frequency.value = frequency;
            osc.type = "square";
            osc.connect(gain);
            gain.connect(ctx.destination);
            const startAt = ctx.currentTime + 0.02;
            osc.start(startAt);
            osc.stop(startAt + beepMs / 1000);
            audioScheduled = true;
        }
    } catch (error) {
        audioError = error instanceof Error ? error.message : String(error);
    }

    return {
        markerId,
        perfNowMs,
        wallClockMs,
        flashMs,
        beepMs,
        frequency,
        audioScheduled,
        audioError,
    };
};
