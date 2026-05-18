(() => {
    if (window.__timeControlReady) {
        return;
    }

    let currentTime = 0;
    let rafId = 0;
    const rafQueue = new Map();

    const originalPerformanceNow = performance.now.bind(performance);
    const originalDateNow = Date.now.bind(Date);
    const originalRequestAnimationFrame = window.requestAnimationFrame.bind(window);
    const originalCancelAnimationFrame = window.cancelAnimationFrame.bind(window);

    const getFrameTime = () => 1000 / (window.__targetFPS || 30);

    performance.now = () => currentTime;
    Date.now = () => Math.floor(currentTime);

    window.requestAnimationFrame = (callback) => {
        rafId += 1;
        rafQueue.set(rafId, callback);
        return rafId;
    };

    window.cancelAnimationFrame = (id) => {
        rafQueue.delete(id);
    };

    window.__advanceFrame = async (frameCount = 1) => {
        const steps = Math.max(1, Number(frameCount) || 1);

        for (let i = 0; i < steps; i += 1) {
            currentTime += getFrameTime();

            const callbacks = Array.from(rafQueue.values());
            rafQueue.clear();

            for (const callback of callbacks) {
                try {
                    callback(currentTime);
                } catch (error) {
                    console.error("requestAnimationFrame callback failed", error);
                }
            }

            await Promise.resolve();
        }
    };

    window.__disableTimeControl = () => {
        performance.now = originalPerformanceNow;
        Date.now = originalDateNow;
        window.requestAnimationFrame = originalRequestAnimationFrame;
        window.cancelAnimationFrame = originalCancelAnimationFrame;
        rafQueue.clear();
        window.__timeControlReady = false;
    };

    window.__timeControlReady = true;
})();
