
"use strict";

// Các thành phần giao diện
const latitudeInput = document.getElementById("latitude");
const longitudeInput = document.getElementById("longitude");
const languageSelect = document.getElementById("language");

const gpsButton = document.getElementById("gpsButton");
const detectButton = document.getElementById("detectButton");
const autoGpsButton = document.getElementById("autoGpsButton");
const autoGpsStatus = document.getElementById("autoGpsStatus");

const statusMessage = document.getElementById("statusMessage");
const locationList = document.getElementById("locationList");
const resultCard = document.getElementById("resultCard");

const locationName = document.getElementById("locationName");
const distanceInfo = document.getElementById("distanceInfo");
const languageInfo = document.getElementById("languageInfo");
const narrationText = document.getElementById("narrationText");

const audioSection = document.getElementById("audioSection");
const audioPlayer = document.getElementById("audioPlayer");
const cacheInfo = document.getElementById("cacheInfo");
const fallbackNotice = document.getElementById("fallbackNotice");

const languageNames = {
    vi: "Tiếng Việt",
    en: "English",
    ja: "日本語"
};

const SEARCH_RADIUS = 500;
const MIN_MOVEMENT_METERS = 25;
const MIN_REFRESH_INTERVAL_MS = 5000;

let nearbyLocations = [];
let selectedLocationId = null;

let watchId = null;
let autoGpsEnabled = false;
let lastSearchPosition = null;
let lastSearchTime = 0;

let listController = null;
let narrationController = null;
let listVersion = 0;
let narrationVersion = 0;


// Thông báo trạng thái
function showStatus(message, type = "") {
    statusMessage.textContent = message;
    statusMessage.className = type;
}


// Tính khoảng cách giữa hai tọa độ GPS
function distanceMeters(lat1, lon1, lat2, lon2) {
    const radians = Math.PI / 180;
    const deltaLat = (lat2 - lat1) * radians;
    const deltaLon = (lon2 - lon1) * radians;

    const a =
        Math.sin(deltaLat / 2) ** 2 +
        Math.cos(lat1 * radians) *
        Math.cos(lat2 * radians) *
        Math.sin(deltaLon / 2) ** 2;

    return 2 * 6371000 *
        Math.asin(Math.sqrt(Math.min(1, Math.max(0, a))));
}


// Kiểm tra tọa độ nhập vào
function readCoordinates() {
    const latitudeText = latitudeInput.value.trim();
    const longitudeText = longitudeInput.value.trim();

    if (!latitudeText || !longitudeText) {
        throw new Error("Vui lòng nhập đủ tọa độ GPS.");
    }

    const latitude = Number(latitudeText);
    const longitude = Number(longitudeText);

    if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        latitude < -90 || latitude > 90 ||
        longitude < -180 || longitude > 180
    ) {
        throw new Error("Tọa độ GPS không hợp lệ.");
    }

    return { latitude, longitude };
}


// Dừng MP3 hiện tại và xóa kết quả thuyết minh
function clearNarration() {
    narrationVersion++;

    if (narrationController) {
        narrationController.abort();
        narrationController = null;
    }

    audioPlayer.pause();
    audioPlayer.removeAttribute("src");
    audioPlayer.load();

    resultCard.hidden = true;
    audioSection.hidden = true;
    fallbackNotice.hidden = true;
    fallbackNotice.textContent = "";
}


// Hiển thị thuyết minh đã lấy được
function displayNarration(data, distance) {
    resultCard.hidden = false;

    locationName.textContent =
        data.location_name || "Địa điểm";

    distanceInfo.textContent =
        `Khoảng cách: ${Math.round(distance)} m`;

    
const requestedName =
    languageNames[data.requested_language] ||
    data.requested_language;

const actualName =
    languageNames[data.content_language] ||
    data.content_language ||
    "Không xác định";

languageInfo.textContent =
    `Ngôn ngữ thuyết minh: ${actualName}`;

if (data.fallback_used) {
    languageInfo.textContent +=
        ` (thay cho ${requestedName})`;
}

    narrationText.textContent =
        data.text || "Chưa có nội dung.";

    if (data.audio_url) {
        audioSection.hidden = false;
        audioPlayer.src = data.audio_url;

        cacheInfo.textContent = data.cache_hit
            ? "MP3 được lấy từ cache."
            : "MP3 vừa được tạo.";
    }
    
fallbackNotice.hidden = true;
fallbackNotice.textContent = "";

if (data.fallback_used) {
    const requestedName =
        languageNames[data.requested_language] ||
        data.requested_language;

    const actualName =
        languageNames[data.content_language] ||
        data.content_language;

    fallbackNotice.textContent =
        `Không có nội dung ${requestedName}. ` +
        `Đang sử dụng bản ${actualName} thay thế.`;

    // Hiển thị cảnh báo trong khu vực nghe thuyết minh.
    audioSection.hidden = false;
    fallbackNotice.hidden = false;
}


    
if (data.status === "success") {
    if (data.fallback_used) {
        showStatus(
            `Không tìm thấy nội dung ${requestedName}. ` +
            `Hệ thống sử dụng nội dung ${actualName} thay thế. ` +
            "Nhấn Play để nghe.",
            "warning"
        );
    } else {
        showStatus(
            `Đã tải thuyết minh ${actualName}. ` +
            "Nhấn Play để nghe.",
            "success"
        );
    }
} else if (data.status === "text_only") {
    showStatus(
        data.message || "Có nội dung nhưng chưa tạo được MP3.",
        "warning"
    );
} else {
    showStatus(
        data.message || "Không tìm thấy nội dung thuyết minh.",
        "error"
    );
}
}


// Tạo các dòng danh sách POI
function renderLocations() {
    locationList.replaceChildren();

    if (nearbyLocations.length === 0) {
        const empty = document.createElement("p");
        empty.className = "empty-message";
        empty.textContent =
            "Không tìm thấy địa điểm đã lưu trong phạm vi 500 mét.";

        locationList.appendChild(empty);
        return;
    }

    for (const item of nearbyLocations) {
        const location = item.location;

        const row = document.createElement("div");
        row.className = "location-item";

        if (location.id === selectedLocationId) {
            row.classList.add("selected");
        }

        const info = document.createElement("div");
        info.className = "location-info";

        const title = document.createElement("h3");
        title.textContent = location.name;

        const description = document.createElement("p");
        description.textContent =
            `Cách ${Math.round(item.distance_meters)} m`;

        const button = document.createElement("button");
        button.type = "button";
        button.className = "location-action";
        button.textContent = "Thuyết minh";
        button.disabled = !location.is_ready;

        if (!location.is_ready) {
            button.textContent = "Chưa sẵn sàng";
        }

        button.addEventListener("click", () => {
            void selectLocation(item);
        });

        info.append(title, description);
        row.append(info, button);
        locationList.appendChild(row);
    }
}


// Lấy toàn bộ POI trong 500m từ SQLite
async function loadNearby(latitude, longitude) {
    if (listController) {
        listController.abort();
    }

    const controller = new AbortController();
    listController = controller;
    const version = ++listVersion;

    const params = new URLSearchParams({
        latitude: String(latitude),
        longitude: String(longitude),
        radius: String(SEARCH_RADIUS)
    });

    detectButton.disabled = true;

    try {
        const response = await fetch(
            `/narration/nearby?${params.toString()}`,
            { signal: controller.signal }
        );

        if (!response.ok) {
            throw new Error("Không thể tải danh sách địa điểm.");
        }

        const data = await response.json();

        if (version !== listVersion) {
            return;
        }

        nearbyLocations = data;
        selectedLocationId = null;

        clearNarration();
        renderLocations();

        showStatus(
            `Đã tìm thấy ${data.length} địa điểm trong 500 mét.`,
            "success"
        );

        lastSearchPosition = { latitude, longitude };
        lastSearchTime = Date.now();

    } catch (error) {
        if (error.name !== "AbortError") {
            showStatus(error.message, "error");
        }
    } finally {
        if (listController === controller) {
            listController = null;
            detectButton.disabled = false;
        }
    }
}


// Người dùng chọn đúng POI muốn nghe
async function selectLocation(item) {
    const location = item.location;

    clearNarration();

    selectedLocationId = location.id;
    renderLocations();

    const version = narrationVersion;
    const controller = new AbortController();
    narrationController = controller;

    const selectedLanguage = languageSelect.value;

    showStatus(
        `Đang chuẩn bị thuyết minh: ${location.name}...`
    );

    try {
        const params = new URLSearchParams({
            language: selectedLanguage
        });

        const response = await fetch(
            `/narration/locations/${location.id}?${params}`,
            {
                method: "POST",
                signal: controller.signal
            }
        );

        const data = await response.json();

        if (!response.ok) {
            const detail = data.detail;

            throw new Error(
                typeof detail === "string"
                    ? detail
                    : detail?.message || "Không thể lấy thuyết minh."
            );
        }

        if (version !== narrationVersion) {
            return;
        }

        displayNarration(data, item.distance_meters);

    } catch (error) {
        if (
            error.name !== "AbortError" &&
            version === narrationVersion
        ) {
            showStatus(error.message, "error");
        }
    } finally {
        if (narrationController === controller) {
            narrationController = null;
        }
    }
}


// Tìm theo tọa độ đang nhập
function searchFromInputs() {
    try {
        const coords = readCoordinates();
        void loadNearby(coords.latitude, coords.longitude);
    } catch (error) {
        showStatus(error.message, "error");
    }
}


// Lấy GPS thiết bị một lần
function getCurrentLocation() {
    if (!navigator.geolocation) {
        showStatus("Trình duyệt không hỗ trợ GPS.", "error");
        return;
    }

    gpsButton.disabled = true;
    showStatus("Đang lấy GPS hiện tại...");

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            latitudeInput.value = latitude.toFixed(6);
            longitudeInput.value = longitude.toFixed(6);

            gpsButton.disabled = false;
            void loadNearby(latitude, longitude);
        },
        (error) => {
            showStatus(
                "Không thể lấy GPS: " + error.message,
                "error"
            );
            gpsButton.disabled = false;
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}


// GPS tự động: chỉ cập nhật danh sách, không phát MP3
function onPositionChanged(position) {
    if (!autoGpsEnabled) {
        return;
    }

    const latitude = position.coords.latitude;
    const longitude = position.coords.longitude;
    const accuracy = position.coords.accuracy;

    latitudeInput.value = latitude.toFixed(6);
    longitudeInput.value = longitude.toFixed(6);

    if (accuracy > 100) {
        autoGpsStatus.textContent =
            "GPS chưa đủ chính xác để cập nhật danh sách.";
        return;
    }

    if (Date.now() - lastSearchTime < MIN_REFRESH_INTERVAL_MS) {
        return;
    }

    if (lastSearchPosition) {
        const moved = distanceMeters(
            lastSearchPosition.latitude,
            lastSearchPosition.longitude,
            latitude,
            longitude
        );

        if (moved < MIN_MOVEMENT_METERS) {
            return;
        }
    }

    autoGpsStatus.textContent =
        "Đang cập nhật danh sách địa điểm...";

    void loadNearby(latitude, longitude);
}


// Bật theo dõi GPS
function startAutoGps() {
    if (!navigator.geolocation) {
        showStatus("Thiết bị không hỗ trợ GPS.", "error");
        return;
    }

    autoGpsEnabled = true;
    lastSearchPosition = null;
    lastSearchTime = 0;

    autoGpsButton.textContent = "Tắt theo dõi GPS";
    autoGpsButton.classList.add("active");
    autoGpsButton.setAttribute("aria-pressed", "true");

    autoGpsStatus.textContent = "Đang chờ GPS...";

    watchId = navigator.geolocation.watchPosition(
        onPositionChanged,
        (error) => {
            autoGpsStatus.textContent =
                "Lỗi GPS: " + error.message;

            if (error.code === 1) {
                stopAutoGps();
                autoGpsStatus.textContent =
                    "Đã tắt GPS vì chưa được cấp quyền vị trí.";
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}


// Tắt theo dõi GPS
function stopAutoGps() {
    autoGpsEnabled = false;

    if (watchId !== null) {
        navigator.geolocation.clearWatch(watchId);
        watchId = null;
    }

    autoGpsButton.textContent = "Bật theo dõi GPS";
    autoGpsButton.classList.remove("active");
    autoGpsButton.setAttribute("aria-pressed", "false");

    autoGpsStatus.textContent = "GPS tự động đã tắt.";
}


// Các sự kiện
detectButton.addEventListener("click", searchFromInputs);
gpsButton.addEventListener("click", getCurrentLocation);

autoGpsButton.addEventListener("click", () => {
    if (autoGpsEnabled) {
        stopAutoGps();
    } else {
        startAutoGps();
    }
});

// Đổi ngôn ngữ thì dừng MP3 cũ.
// Người dùng chọn lại POI để lấy đúng ngôn ngữ mới.
languageSelect.addEventListener("change", () => {
    clearNarration();
    selectedLocationId = null;
    renderLocations();

    showStatus("Đã đổi ngôn ngữ. Hãy chọn địa điểm muốn nghe.");
});

window.addEventListener("pagehide", stopAutoGps);
