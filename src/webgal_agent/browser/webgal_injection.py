"""WebGal 页面注入相关常量与脚本。

这类脚本依赖页面构建产物中的内部符号，脆弱但当前必要。
集中到单个模块至少可以把“依赖哪些符号、为什么这样等待”显式化。
"""

from __future__ import annotations

WEBGAL_SCRIPT_URL_PATTERN = "**/index-e1b3c40e.js"

AUTO_SELECTOR_CANDIDATES = ("#root", "canvas")

NAVIGATE_INJECT_CODE = """window.changeScene = gCe;
window.toggleAuto = wU;"""

RECORD_INJECT_CODE = """
window.changeScene = gCe;
window.toggleAuto = wU;
window.saveConfig = _r;
window.loadConfig = Vh;
window.__webgal = L;
window.hideInfo = () => {
    const el = document.querySelector(`.${ke.main}`);
    el.style.visibility = 'hidden';
};
"""

WAIT_FOR_WEBGAL_READY_JS = """() =>
typeof window.changeScene === 'function' &&
typeof window.toggleAuto === 'function' &&
typeof window.__webgal === 'object' &&
typeof window.hideInfo === 'function'
"""

CHANGE_SCENE_JS = """async (path) => {
    window.changeScene(path, 1);
}"""

POST_SCENE_PREPARE_JS = """async () => {
    await new Promise(r => setTimeout(r, 300));
    window.toggleAuto();
    window.hideInfo();
}"""

APPLY_GAME_CONFIG_JS = """async (overrides) => {
    const setNestedValue = (obj, path, value) => {
        const parts = path.split('.');
        let current = obj;
        for (let i = 0; i < parts.length - 1; i += 1) {
            const key = parts[i];
            if (!current || typeof current !== 'object' || !(key in current)) {
                return false;
            }
            current = current[key];
        }
        const lastKey = parts[parts.length - 1];
        if (!current || typeof current !== 'object') {
            return false;
        }
        current[lastKey] = value;
        return true;
    };

    if (typeof window.saveConfig !== 'function') {
        throw new Error('saveConfig is not available');
    }
    if (typeof window.loadConfig !== 'function') {
        throw new Error('loadConfig is not available');
    }
    if (!window.indexedDB) {
        throw new Error('indexedDB is not available');
    }

    // saveConfig() 会触发 IndexedDB 异步写入；短延迟用于避开同 store 冲突。
    window.saveConfig();
    await new Promise((resolve) => setTimeout(resolve, 200));

    return new Promise((resolve, reject) => {
        const req = indexedDB.open('localforage');

        req.onsuccess = (event) => {
            const db = event.target.result;
            const tx = db.transaction('keyvaluepairs', 'readwrite');
            const store = tx.objectStore('keyvaluepairs');
            const getReq = store.get('MyGO');

            getReq.onsuccess = () => {
                const data = getReq.result;
                if (!data) {
                    resolve(false);
                    return;
                }

                let changed = false;
                for (const [key, value] of Object.entries(overrides)) {
                    changed = setNestedValue(data, key, value) || changed;
                }

                if (!changed) {
                    resolve(false);
                    return;
                }

                const putReq = store.put(data, 'MyGO');
                putReq.onsuccess = () => {
                    window.loadConfig();
                    resolve(true);
                };
                putReq.onerror = () => reject(putReq.error || new Error('put failed'));
            };

            getReq.onerror = () => reject(getReq.error || new Error('get failed'));
            tx.onerror = () => reject(tx.error || new Error('transaction failed'));
        };

        req.onerror = () => reject(req.error || new Error('indexedDB open failed'));
    });
}"""
