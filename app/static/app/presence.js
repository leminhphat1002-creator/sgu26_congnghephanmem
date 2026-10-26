"use strict";

// Cookie ẩn danh dùng chung giữa các tab; server tự hết hạn sau 2 phút.
(() => {
    let pending = false;
    async function heartbeat() {
        if (pending || document.visibilityState !== "visible") return;
        pending = true;
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8000);
        try {
            await fetch("/api/presence/heartbeat", {
                method: "POST", credentials: "same-origin", cache: "no-store",
                signal: controller.signal
            });
        } catch {
            // Mạng lỗi không làm gián đoạn bản đồ hoặc thuyết minh; thử ở nhịp kế tiếp.
        } finally {
            clearTimeout(timeout);
            pending = false;
        }
    }
    setInterval(() => { void heartbeat(); }, 30000);
    document.addEventListener("visibilitychange", () => { void heartbeat(); });
    window.addEventListener("online", () => { void heartbeat(); });
    window.addEventListener("pageshow", () => { void heartbeat(); });
    void heartbeat();
})();
