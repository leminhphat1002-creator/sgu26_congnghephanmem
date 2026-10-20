
"use strict";

// Các thành phần giao diện.
const latitudeInput = document.getElementById("latitude");
const longitudeInput = document.getElementById("longitude");
const languageSelect = document.getElementById("language");

const gpsButton = document.getElementById("gpsButton");
const detectButton = document.getElementById("detectButton");

const statusMessage = document.getElementById("statusMessage");
const resultCard = document.getElementById("resultCard");

const locationName = document.getElementById("locationName");
const distanceInfo = document.getElementById("distanceInfo");
const languageInfo = document.getElementById("languageInfo");
const narrationText = document.getElementById("narrationText");

const audioSection = document.getElementById("audioSection");
const audioPlayer = document.getElementById("audioPlayer");
const cacheInfo = document.getElementById("cacheInfo");

const languageNames = {
    vi: "Tiếng Việt",
    en: "English",
    ja: "日本語"
};


// Hiển thị trạng thái cho người dùng.
function showStatus(message, type = "") {
    statusMessage.textContent = message;
    statusMessage.className = type;
}


// Xóa kết quả cũ.
function clearResult() {
    resultCard.hidden = true;
    audioSection.hidden = true;

    audioPlayer.pause();
    audioPlayer.removeAttribute("src");
    audioPlayer.load();

    locationName.textContent = "";
    distanceInfo.textContent = "";
    languageInfo.textContent = "";
    narrationText.textContent = "";
    cacheInfo.textContent = "";
}


// Lấy vị trí thực tế từ trình duyệt.
function getCurrentLocation() {
    if (!navigator.geolocation) {
        showStatus(
            "Trình duyệt không hỗ trợ lấy vị trí GPS.",
            "error"
        );
        return;
    }

    gpsButton.disabled = true;
    showStatus("Đang lấy vị trí GPS...");

    navigator.geolocation.getCurrentPosition(
        function (position) {
            latitudeInput.value =
                position.coords.latitude.toFixed(6);

            longitudeInput.value =
                position.coords.longitude.toFixed(6);

            showStatus(
                "Đã lấy vị trí GPS thành công.",
                "success"
            );

            gpsButton.disabled = false;
        },

        function (error) {
            let message = "Không thể lấy vị trí GPS.";

            if (error.code === 1) {
                message = "Bạn chưa cấp quyền truy cập vị trí.";
            } else if (error.code === 2) {
                message = "Không xác định được vị trí thiết bị.";
            } else if (error.code === 3) {
                message = "Hết thời gian chờ GPS.";
            }

            showStatus(message, "error");
            gpsButton.disabled = false;
        },

        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}


// Hiển thị kết quả API.
function displayResult(data) {
    clearResult();

    if (data.status === "no_location") {
        showStatus(
            data.message || "Không tìm thấy địa điểm gần bạn.",
            "error"
        );
        return;
    }

    resultCard.hidden = false;

    locationName.textContent =
        data.location_name || "Địa điểm chưa xác định";

    distanceInfo.textContent =
        data.distance_meters != null
            ? `Khoảng cách: ${data.distance_meters} mét`
            : "Chưa có khoảng cách";

    languageInfo.textContent =
        "Ngôn ngữ: " +
        (languageNames[data.content_language] ||
            data.content_language ||
            "Không xác định");

    narrationText.textContent =
        data.text || "Chưa có nội dung thuyết minh.";

    if (data.fallback_used) {
        languageInfo.textContent += " (đã dùng fallback)";
    }

    if (data.audio_url) {
        audioSection.hidden = false;

        audioPlayer.src = data.audio_url;

        cacheInfo.textContent = data.cache_hit
            ? "Âm thanh được lấy từ cache."
            : "Âm thanh vừa được tạo mới.";
    }

    if (data.status === "success") {
        showStatus(
            "Phát hiện địa điểm và tạo thuyết minh thành công.",
            "success"
        );
    } else if (data.status === "text_only") {
        showStatus(
            data.message || "Chỉ có nội dung văn bản.",
            "error"
        );
    } else {
        showStatus(
            data.message || "Chưa có nội dung thuyết minh.",
            "error"
        );
    }
}


// Gửi GPS và ngôn ngữ đến FastAPI.
async function detectNarration() {
    const latitudeText = latitudeInput.value.trim();
    const longitudeText = longitudeInput.value.trim();

    if (!latitudeText || !longitudeText) {
        showStatus(
            "Vui lòng nhập đủ vĩ độ và kinh độ.",
            "error"
        );
        return;
    }

    const latitude = Number(latitudeText);
    const longitude = Number(longitudeText);
    const language = languageSelect.value;

    if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        latitude < -90 ||
        latitude > 90 ||
        longitude < -180 ||
        longitude > 180
    ) {
        showStatus("Tọa độ GPS không hợp lệ.", "error");
        return;
    }

    clearResult();
    detectButton.disabled = true;
    detectButton.textContent = "Đang xử lý...";

    showStatus(
        "Đang tìm địa điểm, lấy nội dung và tạo giọng nói..."
    );

    try {
        const response = await fetch("/narration/detect", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                latitude: latitude,
                longitude: longitude,
                language: language
            })
        });

        const data = await response.json();

        if (!response.ok) {
            const detail = data.detail;

            let errorMessage = "Yêu cầu không thành công.";

            if (typeof detail === "string") {
                errorMessage = detail;
            } else if (detail && typeof detail === "object") {
                errorMessage =
                    detail.message || JSON.stringify(detail);
            }

            throw new Error(errorMessage);
        }

        displayResult(data);

    } catch (error) {
        showStatus(
            error.message || "Không thể kết nối máy chủ.",
            "error"
        );
    } finally {
        detectButton.disabled = false;
        detectButton.textContent =
            "Phát hiện và thuyết minh";
    }
}


// Gán sự kiện cho các nút.
gpsButton.addEventListener("click", getCurrentLocation);
detectButton.addEventListener("click", detectNarration);
