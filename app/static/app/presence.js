"use strict";

// Cookie ẩn danh dùng chung giữa các tab; server tự hết hạn sau 2 phút.
(() => {
    const share = document.getElementById("shareVisitorLocation");
    const status = document.getElementById("shareVisitorLocationStatus");
    let pending = false;
    let sharingVersion = 0;
    let clearLocation = false;

    function showLocationStatus(message = "") {
        status.hidden = !message;
        status.dataset.i18n = message;
        status.textContent = message ? window.BatTrangI18n.t(message) : "";
    }

    function locate() {
        return new Promise(resolve => {
            if (!navigator.geolocation) {
                resolve(null);
                return;
            }
            const deadline = setTimeout(() => resolve(null), 6000);
            const finish = location => {
                clearTimeout(deadline);
                resolve(location);
            };
            navigator.geolocation.getCurrentPosition(
                ({ coords }) => finish({
                    latitude: Number(coords.latitude.toFixed(3)),
                    longitude: Number(coords.longitude.toFixed(3))
                }),
                () => finish(null),
                { timeout: 5000, maximumAge: 30000 }
            );
        });
    }

    async function heartbeat() {
        if (pending || document.visibilityState !== "visible") return;
        pending = true;
        const version = sharingVersion;
        const controller = new AbortController();
        let timeout;
        try {
            const location = share.checked ? await locate() : null;
            if (version !== sharingVersion || document.visibilityState !== "visible") return;
            const options = {
                method: "POST", credentials: "same-origin", cache: "no-store",
                signal: controller.signal
            };
            if (share.checked || clearLocation) {
                options.headers = { "Content-Type": "application/json" };
                options.body = JSON.stringify({ location });
            }
            timeout = setTimeout(() => controller.abort(), 8000);
            const response = await fetch("/api/presence/heartbeat", options);
            if (version !== sharingVersion) return;
            if (response.ok) clearLocation = false;
            if (share.checked) {
                if (!location) showLocationStatus("Chưa lấy được vị trí.");
                else showLocationStatus(response.ok ? "Đang chia sẻ vị trí gần đúng." : "Chưa gửi được vị trí. Sẽ tự thử lại.");
            }
        } catch {
            // Mạng lỗi không làm gián đoạn bản đồ hoặc thuyết minh; thử ở nhịp kế tiếp.
            if (version === sharingVersion && share.checked) {
                showLocationStatus("Chưa gửi được vị trí. Sẽ tự thử lại.");
            }
        } finally {
            clearTimeout(timeout);
            pending = false;
            if (version !== sharingVersion) void heartbeat();
        }
    }

    share.checked = false;
    share.addEventListener("change", () => {
        sharingVersion++;
        clearLocation = !share.checked;
        showLocationStatus(share.checked ? "Đang lấy vị trí gần đúng…" : "");
        void heartbeat();
    });
    setInterval(() => { void heartbeat(); }, 30000);
    document.addEventListener("visibilitychange", () => { void heartbeat(); });
    window.addEventListener("online", () => { void heartbeat(); });
    window.addEventListener("pageshow", () => { void heartbeat(); });
    void heartbeat();
})();
