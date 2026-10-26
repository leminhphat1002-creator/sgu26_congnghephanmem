"use strict";

const $ = (id) => document.getElementById(id);
let csrfToken = "";
let locations = [];
let editingId = null;
let narrationRows = [];
let contentVersion = 0;
let presenceTimer = null;
let presencePending = false;
const languageNames = { vi: "Tiếng Việt", en: "English", ja: "日本語" };
const actionNames = { login: "Đăng nhập", logout: "Đăng xuất", create_location: "Thêm địa điểm",
    update_location: "Sửa địa điểm", delete_location: "Xóa địa điểm", save_narration: "Lưu thuyết minh",
    delete_narration: "Xóa thuyết minh", create_account: "Tạo tài khoản", reset_account: "Đổi mật khẩu" };

function notify(message, error = false) {
    $("adminMessage").textContent = message;
    $("adminMessage").classList.toggle("error", error);
    $("adminMessage").hidden = false;
}

function showLogin() {
    clearInterval(presenceTimer);
    presenceTimer = null;
    csrfToken = "";
    $("adminView").hidden = true;
    $("loginView").hidden = false;
    $("password").value = "";
}

async function api(path, options = {}) {
    const headers = { ...options.headers };
    if (options.body) headers["Content-Type"] = "application/json";
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;
    const response = await fetch(path, { ...options, headers, credentials: "same-origin" });
    if (response.status === 204) return null;
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        if (response.status === 401 && path !== "/api/admin/login") showLogin();
        let message = data.detail?.message || data.detail || "Yêu cầu chưa thành công.";
        if (Array.isArray(message)) message = message.map((item) => item.msg).join("; ");
        throw new Error(message);
    }
    return data;
}

async function enterAdmin(identity) {
    csrfToken = identity.csrf_token;
    $("accountName").textContent = identity.username;
    $("password").value = "";
    $("loginView").hidden = true;
    $("adminView").hidden = false;
    await refresh();
    await loadQr();
    startPresencePolling();
}

function updatePresence(data) {
    const count = $("activeVisitorsCount");
    if (!count) return;
    count.textContent = String(data.active_visitors);
    $("activeVisitorsNote").textContent = "Trình duyệt khách · 2 phút gần nhất";
}

async function refreshPresence() {
    if (presencePending || $("adminView").hidden || document.visibilityState !== "visible") return;
    presencePending = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
        updatePresence(await api("/api/admin/presence", { signal: controller.signal }));
    } catch {
        if ($("activeVisitorsCount")) {
            $("activeVisitorsCount").textContent = "—";
            $("activeVisitorsNote").textContent = "Chưa cập nhật được · sẽ tự thử lại";
        }
    } finally {
        clearTimeout(timeout);
        presencePending = false;
    }
}

function startPresencePolling() {
    clearInterval(presenceTimer);
    presenceTimer = setInterval(() => { void refreshPresence(); }, 15000);
    void refreshPresence();
}

document.addEventListener("visibilitychange", () => { void refreshPresence(); });
window.addEventListener("pagehide", () => { clearInterval(presenceTimer); });
window.addEventListener("pageshow", () => {
    if (csrfToken && !$("adminView").hidden) startPresencePolling();
});

$("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("loginButton").disabled = true;
    $("loginMessage").textContent = "";
    try {
        const identity = await api("/api/admin/login", { method: "POST", body: JSON.stringify({
            username: $("username").value.trim(), password: $("password").value
        }) });
        await enterAdmin(identity);
    } catch (error) {
        if ($("adminView").hidden) $("loginMessage").textContent = error.message;
        else notify(error.message, true);
    } finally {
        $("loginButton").disabled = false;
    }
});

$("logoutButton").addEventListener("click", async () => {
    try {
        await api("/api/admin/logout", { method: "POST" });
        showLogin();
        $("loginMessage").textContent = "Đã đăng xuất.";
    } catch (error) { notify(error.message, true); }
});

function showPane(name) {
    document.querySelectorAll(".pane").forEach((pane) => { pane.hidden = pane.id !== `pane-${name}`; });
    document.querySelectorAll("[data-pane]").forEach((button) => {
        const active = button.dataset.pane === name;
        button.classList.toggle("active", active);
        if (active) button.setAttribute("aria-current", "page");
        else button.removeAttribute("aria-current");
    });
    $("pageTitle").textContent = { overview: "Tổng quan", locations: "Địa điểm", content: "Thuyết minh", qr: "Mã QR truy cập" }[name];
}
document.querySelectorAll("[data-pane]").forEach((button) => {
    button.addEventListener("click", () => showPane(button.dataset.pane));
});

function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (className) node.className = className;
    return node;
}

function drawDashboard(data) {
    $("stats").replaceChildren();
    const stats = [
        ["KHÁCH ĐANG HOẠT ĐỘNG", data.active_visitors, "Trình duyệt khách · 2 phút gần nhất"],
        ["TỔNG ĐỊA ĐIỂM", data.locations, `${data.published} địa điểm có nội dung hiển thị`],
        ["BẢN THUYẾT MINH", data.narrations, "Nội dung biên soạn trong SQLite"],
        ["YÊU CẦU HÔM NAY", data.requests_today, "Yêu cầu thuyết minh · GMT+7"],
        ["ÂM THANH ĐÃ LƯU", data.audio_files, `${(data.audio_bytes / 1048576).toFixed(1)} MB trong cache`]
    ];
    for (const [label, count, note] of stats) {
        const card = element("article", null, "stat");
        card.append(element("div", label, "stat-label"), element("div", String(count), "stat-number"), element("div", note, "stat-note"));
        if (label === "KHÁCH ĐANG HOẠT ĐỘNG") {
            card.querySelector(".stat-number").id = "activeVisitorsCount";
            card.querySelector(".stat-note").id = "activeVisitorsNote";
            card.title = "Tự cập nhật mỗi 15 giây. Nhiều tab cùng trình duyệt được gộp; tab nền hoặc đã đóng sẽ hết hạn sau 2 phút không có tín hiệu.";
        }
        $("stats").append(card);
    }
    $("usageChart").replaceChildren();
    const max = Math.max(1, ...data.daily.map((day) => day.count));
    for (const day of data.daily) {
        const column = element("div", null, "chart-column");
        const bar = element("div", null, "chart-bar");
        bar.style.height = `${Math.max(2, day.count / max * 115)}px`;
        bar.setAttribute("aria-label", `${day.date}: ${day.count} yêu cầu`);
        column.append(element("span", String(day.count)), bar, element("span", day.date.slice(5).split("-").reverse().join("/")));
        $("usageChart").append(column);
    }
    $("languageStats").replaceChildren();
    for (const [language, name] of Object.entries(languageNames)) {
        const row = element("div", null, "language-row");
        row.append(element("span", name), element("strong", `${data.languages[language] || 0} bài`));
        $("languageStats").append(row);
    }
    $("translationHint").textContent = `Còn ${data.missing_translations} bản ngôn ngữ chưa được biên tập trên tất cả địa điểm.`;
    $("activityBody").replaceChildren();
    for (const item of data.recent_activity) {
        const row = element("tr");
        for (const text of [new Date(item.created_at).toLocaleString("vi-VN"), item.actor, actionNames[item.action] || item.action, item.target || "—"]) row.append(element("td", text));
        $("activityBody").append(row);
    }
    if (!data.recent_activity.length) {
        const row = element("tr");
        const cell = element("td", "Chưa có hoạt động quản lý."); cell.colSpan = 4;
        row.append(cell); $("activityBody").append(row);
    }
}

function drawLocations() {
    const keyword = $("locationSearch").value.trim().toLocaleLowerCase("vi");
    $("locationsBody").replaceChildren();
    const rows = locations.filter((location) => location.name.toLocaleLowerCase("vi").includes(keyword));
    for (const location of rows) {
        const row = element("tr");
        row.append(element("td", location.name), element("td", location.languages.map((lang) => lang.toUpperCase()).join(" · ") || "Chưa có"));
        const status = element("td");
        status.append(element("span", location.is_ready ? "Sẵn sàng" : "Bản nháp", `badge ${location.is_ready ? "ready" : "draft"}`));
        row.append(status);
        const actions = element("td"); const group = element("div", null, "row-actions");
        for (const [label, handler, className] of [
            ["Sửa", () => editLocation(location), "secondary"],
            ["Bài viết", () => openContent(location.id), "secondary"],
            ["Xóa", () => removeLocation(location), "danger-outline"]
        ]) {
            const button = element("button", label, className); button.type = "button";
            button.setAttribute("aria-label", `${label}: ${location.name}`);
            button.addEventListener("click", handler); group.append(button);
        }
        actions.append(group); row.append(actions); $("locationsBody").append(row);
    }
    if (!rows.length) {
        const row = element("tr"); const cell = element("td", "Chưa có địa điểm phù hợp."); cell.colSpan = 4;
        row.append(cell); $("locationsBody").append(row);
    }
}

async function refresh() {
    const [dashboard, list] = await Promise.all([api("/api/admin/dashboard"), api("/api/admin/locations")]);
    locations = list;
    drawDashboard(dashboard); drawLocations();
    const selected = $("contentLocation").value;
    $("contentLocation").replaceChildren();
    for (const location of locations) {
        const option = element("option", location.name); option.value = location.id; $("contentLocation").append(option);
    }
    if (locations.some((item) => String(item.id) === selected)) $("contentLocation").value = selected;
    await loadNarrations();
}
$("refreshButton").addEventListener("click", () => refresh().then(() => notify("Đã cập nhật dữ liệu.")).catch((error) => notify(error.message, true)));
$("locationSearch").addEventListener("input", drawLocations);

function editLocation(location = null) {
    editingId = location?.id || null;
    $("locationEditorTitle").textContent = location ? `Sửa địa điểm #${location.id}` : "Thêm địa điểm";
    $("locationNameInput").value = location?.name || "";
    $("descriptionInput").value = location?.description_source || "";
    $("latitudeInput").value = location?.latitude ?? "";
    $("longitudeInput").value = location?.longitude ?? "";
    $("radiusInput").value = location?.radius || 80;
    $("readyInput").checked = location?.is_ready || false;
    $("locationNameInput").focus();
}
$("newLocationButton").addEventListener("click", () => editLocation());
$("cancelEditButton").addEventListener("click", () => editLocation());

$("locationForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const lat = $("latitudeInput").value.trim(), lon = $("longitudeInput").value.trim();
    if (Boolean(lat) !== Boolean(lon)) { notify("Cần nhập đủ cả vĩ độ và kinh độ, hoặc để trống cả hai.", true); return; }
    const body = { name: $("locationNameInput").value.trim(), description_source: $("descriptionInput").value.trim(),
        latitude: lat ? Number(lat) : null, longitude: lon ? Number(lon) : null,
        radius: Number($("radiusInput").value), is_ready: $("readyInput").checked };
    $("saveLocationButton").disabled = true;
    try {
        await api(editingId ? `/locations/${editingId}` : "/locations", { method: editingId ? "PUT" : "POST", body: JSON.stringify(body) });
        await refresh(); editLocation(); notify("Đã lưu địa điểm. Bạn có thể biên tập bài trong mục Thuyết minh.");
    } catch (error) { notify(error.message, true); }
    finally { $("saveLocationButton").disabled = false; }
});

async function confirmDeletion(title, description) {
    $("deleteTitle").textContent = title; $("deleteDescription").textContent = description;
    const dialog = $("deleteDialog"); dialog.returnValue = "cancel"; dialog.showModal();
    return new Promise((resolve) => dialog.addEventListener("close", () => resolve(dialog.returnValue === "confirm"), { once: true }));
}
async function removeLocation(location) {
    if (!await confirmDeletion(`Xóa ${location.name}?`, "Địa điểm và các bản thuyết minh của nó sẽ bị xóa. Thao tác này không có nút hoàn tác.")) return;
    try { await api(`/locations/${location.id}`, { method: "DELETE" }); await refresh(); if (editingId === location.id) editLocation(); notify("Đã xóa địa điểm."); }
    catch (error) { notify(error.message, true); }
}

async function openContent(id) {
    showPane("content"); $("contentLocation").value = String(id); await loadNarrations();
}

async function loadNarrations() {
    const id = $("contentLocation").value;
    const version = ++contentVersion;
    $("saveContentButton").disabled = true;
    $("deleteContentButton").disabled = true;
    $("contentLanguage").disabled = true;
    narrationRows = [];
    $("contentTitle").value = ""; $("contentText").value = "";
    if (!id) { $("contentState").textContent = "Thêm địa điểm trước khi tạo nội dung."; return; }
    try {
        const rows = await api(`/api/admin/locations/${id}/narrations`);
        if (version !== contentVersion) return;
        narrationRows = rows; populateNarration(); $("saveContentButton").disabled = false;
        $("contentLanguage").disabled = false;
    } catch (error) { notify(error.message, true); }
}
function populateNarration() {
    const row = narrationRows.find((item) => item.language === $("contentLanguage").value);
    $("contentTitle").value = row?.title || ""; $("contentText").value = row?.content || "";
    $("contentState").textContent = row ? "Đang chỉnh sửa bản đã lưu." : "Chưa có bản ngôn ngữ này. Nhập nội dung để bổ sung.";
    $("deleteContentButton").disabled = !row;
    $("charCount").textContent = `${$("contentText").value.length} / 900 ký tự`;
}
$("contentLocation").addEventListener("change", () => void loadNarrations());
$("contentLanguage").addEventListener("change", populateNarration);
$("contentText").addEventListener("input", () => { $("charCount").textContent = `${$("contentText").value.length} / 900 ký tự`; });

$("narrationForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const id = $("contentLocation").value, language = $("contentLanguage").value;
    if (!id) return;
    $("saveContentButton").disabled = true;
    try {
        await api(`/api/admin/locations/${id}/narrations/${language}`, { method: "PUT", body: JSON.stringify({ title: $("contentTitle").value, content: $("contentText").value }) });
        await refresh(); notify(`Đã lưu bản ${languageNames[language]}.`);
    } catch (error) { notify(error.message, true); }
    finally { $("saveContentButton").disabled = false; }
});
$("deleteContentButton").addEventListener("click", async () => {
    const id = $("contentLocation").value, language = $("contentLanguage").value;
    if (!id || !await confirmDeletion(`Xóa bản ${languageNames[language]}?`, "Chỉ xóa bài của ngôn ngữ đang chọn. Những bản còn lại được giữ nguyên.")) return;
    try { await api(`/api/admin/locations/${id}/narrations/${language}`, { method: "DELETE" }); await refresh(); notify("Đã xóa bản thuyết minh."); }
    catch (error) { notify(error.message, true); }
});

async function loadQr() {
    try {
        const data = await api("/api/share"); $("qrTarget").textContent = data.url;
        const host = new URL(data.url).hostname;
        const lan = /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host);
        $("qrHint").textContent = data.local_only ? "Địa chỉ localhost chỉ mở trên máy chủ. Cấu hình PUBLIC_BASE_URL bằng IP LAN hoặc tên miền để điện thoại quét được."
            : lan ? "Điện thoại cần kết nối cùng mạng Wi-Fi với máy chủ. Đây là liên kết nội bộ, chưa phải website công khai trên Internet."
            : "Quét bằng camera điện thoại để mở trang khám phá.";
    } catch (error) { notify(error.message, true); }
}

void api("/api/admin/me").then(enterAdmin).catch(() => showLogin());
