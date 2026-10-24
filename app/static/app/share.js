"use strict";

let shareUrl = "";
async function loadShare() {
    const hint = document.getElementById("shareHint");
    try {
        const response = await fetch("/api/share");
        if (!response.ok) throw new Error("Chưa cấu hình được đường dẫn QR.");
        const data = await response.json();
        shareUrl = data.url;
        document.getElementById("shareUrl").textContent = shareUrl;
        const host = new URL(shareUrl).hostname;
        const lan = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host);
        hint.textContent = data.local_only
            ? "Mã hiện trỏ về localhost, điện thoại chưa mở được. Cần cấu hình địa chỉ LAN hoặc tên miền."
            : lan ? "Điện thoại và máy chủ cần cùng mạng Wi-Fi. Giữ máy chủ đang chạy."
            : "Khách có thể quét mã để mở trang khám phá.";
    } catch (error) {
        hint.textContent = error.message;
    }
}
document.getElementById("copyShare").addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(shareUrl);
        document.getElementById("shareHint").textContent = "Đã sao chép liên kết.";
    } catch {
        document.getElementById("shareHint").textContent = "Hãy sao chép địa chỉ hiển thị phía trên.";
    }
});
document.getElementById("printShare").addEventListener("click", () => window.print());
void loadShare();
