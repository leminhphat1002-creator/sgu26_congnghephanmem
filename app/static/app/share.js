"use strict";
const t = window.BatTrangI18n.t;
window.BatTrangI18n.init();

let shareUrl = "";
async function loadShare() {
    const hint = document.getElementById("shareHint");
    try {
        const response = await fetch("/api/share");
        if (!response.ok) throw new Error(t("Chưa cấu hình được đường dẫn QR."));
        const data = await response.json();
        shareUrl = data.url;
        document.getElementById("shareUrl").textContent = shareUrl;
        const host = new URL(shareUrl).hostname;
        const lan = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host);
        hint.textContent = data.local_only
            ? t("Mã hiện trỏ về localhost, điện thoại chưa mở được. Cần cấu hình địa chỉ LAN hoặc tên miền.")
            : lan ? t("Điện thoại và máy chủ cần cùng mạng Wi-Fi. Giữ máy chủ đang chạy.")
            : t("Khách có thể quét mã để mở trang khám phá.");
    } catch (error) {
        hint.textContent = t("Chưa cấu hình được đường dẫn QR.");
    }
}
document.getElementById("copyShare").addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(shareUrl);
        document.getElementById("shareHint").textContent = t("Đã sao chép liên kết.");
    } catch {
        document.getElementById("shareHint").textContent = t("Hãy sao chép địa chỉ hiển thị phía trên.");
    }
});
document.getElementById("printShare").addEventListener("click", () => window.print());
void loadShare();
