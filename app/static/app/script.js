
"use strict";
const t = window.BatTrangI18n.t;
window.BatTrangI18n.init();

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
const locationReference = document.getElementById("locationReference");
const locationSource = document.getElementById("locationSource");
const narrationText = document.getElementById("narrationText");

const audioSection = document.getElementById("audioSection");
const audioPlayer = document.getElementById("audioPlayer");
const cacheInfo = document.getElementById("cacheInfo");
const fallbackNotice = document.getElementById("fallbackNotice");
const audioStatus = document.getElementById("audioStatus");
const retryAudioButton = document.getElementById("retryAudioButton");
const deviceSpeechButton = document.getElementById("deviceSpeechButton");
const stopSpeechButton = document.getElementById("stopSpeechButton");
const deviceSpeech = window.speechSynthesis;
let currentNarrationData = null;
let activeSpeech = null;

const languageNames = window.BatTrangI18n.names;

const SEARCH_RADIUS = 500;
let explorationMode = "remote";
let dataMode = "remote";
const modeStatus = document.getElementById("modeStatus");
let gpsVersion = 0;
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
const mapResultLink = document.getElementById("mapResultLink");
let locationMap = null;
const locationSearch = document.getElementById("locationSearch");
const clearSearchButton = document.getElementById("clearSearchButton");
const retryNarrationButton = document.getElementById("retryNarrationButton");
let pendingNarrationKey = null;
let loadedNarrationKey = null;

function normalizeSearch(value) {
    return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase().trim();
}

function visibleLocations() {
    const words = normalizeSearch(locationSearch.value).split(/\s+/).filter(Boolean);
    return nearbyLocations.filter(item => {
        const name = normalizeSearch(`${item.location.name} ${t(item.location.name)}`);
        return words.every(word => name.includes(word));
    });
}

function selectedItem() {
    return nearbyLocations.find(item => item.location.id === selectedLocationId);
}

function revealNarration() {
    if (!resultCard.hidden) resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function updateDistanceInfo(distance) {
    distanceInfo.textContent = distance == null
        ? t("Khám phá từ xa — không sử dụng GPS")
        : `${t(dataMode === "demo" ? t("Từ vị trí mẫu") : t("Từ vị trí tìm kiếm"))}: ${Math.round(distance)} m`;
}

function updateLocationReference(location) {
    locationReference.textContent = t(location?.description_source);
    locationSource.hidden = true;
    locationSource.removeAttribute("href");
    if (!location?.source_url) return;
    try {
        const url = new URL(location.source_url);
        if (!["https:", "http:"].includes(url.protocol)) return;
        locationSource.href = url.href;
        locationSource.hidden = false;
    } catch { /* An invalid source must not prevent reading the guide. */ }
}


// Thông báo trạng thái
function showStatus(message, type = "") {
    statusMessage.textContent = message;
    statusMessage.className = type;
    const mapStatus = document.getElementById("mapStatus");
    mapStatus.textContent = message;
    mapStatus.className = type;
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
        throw new Error(t("Vui lòng nhập đủ tọa độ GPS."));
    }

    const latitude = Number(latitudeText);
    const longitude = Number(longitudeText);

    if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude) ||
        latitude < -90 || latitude > 90 ||
        longitude < -180 || longitude > 180
    ) {
        throw new Error(t("Tọa độ GPS không hợp lệ."));
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
    stopDeviceSpeech();
    currentNarrationData = null;

    audioPlayer.pause();
    audioPlayer.removeAttribute("src");
    audioPlayer.load();

    resultCard.hidden = true;
    resultCard.setAttribute("aria-busy", "false");
    pendingNarrationKey = null;
    loadedNarrationKey = null;
    retryNarrationButton.hidden = true;
    mapResultLink.hidden = true;
    audioSection.hidden = true;
    audioPlayer.hidden = true;
    cacheInfo.textContent = "";
    audioStatus.textContent = "";
    retryAudioButton.hidden = true;
    fallbackNotice.hidden = true;
    fallbackNotice.textContent = "";
}


// Hiển thị thuyết minh đã lấy được
function displayNarration(data, distance) {
    resultCard.hidden = false;
    resultCard.setAttribute("aria-busy", "false");
    mapResultLink.hidden = false;

    locationName.textContent =
        t(data.location_name) || t("Địa điểm");

    updateDistanceInfo(distance);
    updateLocationReference(selectedItem()?.location);
    retryNarrationButton.hidden = Boolean(data.text);


    const requestedName =
        languageNames[data.requested_language] ||
        data.requested_language;

    const actualName =
        languageNames[data.content_language] ||
        data.content_language ||
        t("Không xác định");

    languageInfo.textContent =
        t("Ngôn ngữ thuyết minh: {language}", { language: actualName });

    if (data.fallback_used) {
        languageInfo.textContent +=
            t(" (thay cho {language})", { language: requestedName });
    }

    narrationText.textContent =
        data.text || t("Chưa có nội dung.");
    currentNarrationData = data.text ? data : null;
    audioSection.hidden = !data.text;
    updateDeviceVoice();

    if (data.stream_url || data.audio_url) {
        audioSection.hidden = false;
        audioPlayer.src = data.stream_url || data.audio_url;
        audioPlayer.hidden = false;
        audioStatus.textContent = t("Nhấn Play để nghe thuyết minh.");
        cacheInfo.textContent = t("Giọng đọc tại máy chủ, dùng được khi máy chủ không có Internet.");
    }


    if (data.status === "success") {
        if (data.fallback_used) {
            showStatus(
                t("Không có bản {requested}. Đang dùng bản {actual}. Bạn có thể đọc bài bên dưới.", { requested: requestedName, actual: actualName }),
                "warning"
            );
        } else {
            showStatus(
                t("Đã tải thuyết minh {language}. Bạn có thể đọc bài ngay bên dưới.", { language: actualName }),
                "success"
            );
        }
    } else if (data.status === "text_only") {
        showStatus(
            t("Có nội dung nhưng chưa tạo được MP3."),
            "warning"
        );
    } else {
        showStatus(
            t("Không tìm thấy nội dung thuyết minh."),
            "error"
        );
    }
}


function stopDeviceSpeech() {
    // Xóa tham chiếu trước cancel để bỏ qua sự kiện của bài cũ.
    activeSpeech = null;
    deviceSpeech?.cancel();
    deviceSpeechButton.textContent = t("Nghe bằng giọng thiết bị");
    stopSpeechButton.hidden = true;
}

function matchingDeviceVoice() {
    const language = currentNarrationData?.content_language;
    return deviceSpeech?.getVoices().find(voice =>
        voice.lang.toLowerCase().split(/[-_]/)[0] === language
    );
}

function updateDeviceVoice() {
    const available = Boolean(deviceSpeech && window.SpeechSynthesisUtterance && matchingDeviceVoice());
    deviceSpeechButton.hidden = !currentNarrationData || !available;
    deviceSpeechButton.disabled = !available;
    // Giọng thiết bị là lựa chọn phụ; thiếu giọng không phải lỗi của trình phát tại máy chủ.
    fallbackNotice.hidden = true;
}

deviceSpeech?.addEventListener("voiceschanged", updateDeviceVoice);
deviceSpeechButton.addEventListener("click", () => {
    if (!currentNarrationData || !deviceSpeech) return;
    if (activeSpeech && deviceSpeech.paused) {
        deviceSpeech.resume();
        deviceSpeechButton.textContent = t("Tạm dừng đọc");
        return;
    }
    if (activeSpeech) {
        deviceSpeech.pause();
        deviceSpeechButton.textContent = t("Tiếp tục đọc");
        return;
    }
    const voice = matchingDeviceVoice();
    if (!voice) return updateDeviceVoice();
    audioPlayer.pause();
    const speech = new SpeechSynthesisUtterance(currentNarrationData.text);
    activeSpeech = speech;
    speech.voice = voice;
    speech.lang = voice.lang;
    speech.onend = () => { if (activeSpeech === speech) stopDeviceSpeech(); };
    speech.onerror = () => {
        if (activeSpeech !== speech) return;
        stopDeviceSpeech();
        fallbackNotice.hidden = false;
        fallbackNotice.textContent = t("Thiết bị chưa đọc được bài. Bạn vẫn có thể đọc nội dung hoặc dùng MP3.");
    };
    deviceSpeechButton.textContent = t("Tạm dừng đọc");
    stopSpeechButton.hidden = false;
    deviceSpeech.speak(speech);
});
stopSpeechButton.addEventListener("click", stopDeviceSpeech);
audioPlayer.addEventListener("play", stopDeviceSpeech);

// Phát trực tiếp từ bộ đọc cục bộ; không gọi API tạo giọng qua Internet.
audioPlayer.addEventListener("waiting", () => {
    if (currentNarrationData && !audioPlayer.paused) audioStatus.textContent = t("Đang mở giọng đọc…");
});
audioPlayer.addEventListener("playing", () => {
    audioStatus.textContent = t("Đang đọc thuyết minh.");
    retryAudioButton.hidden = true;
});
audioPlayer.addEventListener("pause", () => {
    if (currentNarrationData && !audioPlayer.ended) {
        audioStatus.textContent = t("Đã tạm dừng. Nhấn Play để tiếp tục.");
    }
});
audioPlayer.addEventListener("ended", () => {
    audioStatus.textContent = t("Đã đọc xong. Nhấn Play để nghe lại.");
});
audioPlayer.addEventListener("error", () => {
    if (!currentNarrationData) return;
    audioStatus.textContent = t("Chưa mở được âm thanh. Bạn có thể thử phát lại hoặc tải lại bài nếu nội dung vừa thay đổi.");
    retryAudioButton.hidden = false;
    retryNarrationButton.hidden = false;
});
retryAudioButton.addEventListener("click", () => {
    if (!currentNarrationData) return;
    retryAudioButton.hidden = true;
    audioPlayer.load();
    void audioPlayer.play().catch(() => {
        retryAudioButton.hidden = false;
    });
});


// Tạo các dòng danh sách POI
function renderLocations() {
    const items = visibleLocations();
    locationMap?.setLocations(items, selectedLocationId);
    clearSearchButton.hidden = !locationSearch.value;
    locationList.replaceChildren();

    if (items.length === 0) {
        const empty = document.createElement("p");
        empty.className = "empty-message";
        empty.textContent = locationSearch.value.trim()
            ? t("Không có điểm phù hợp. Hãy thử từ khóa khác hoặc xóa bộ lọc.")
            : t("Chưa có địa điểm trong phạm vi này. Chọn Khám phá từ xa để xem toàn bộ địa điểm.");

        locationList.appendChild(empty);
        return;
    }

    const nearest = items.filter(item => Number.isFinite(item.distance_meters))
        .reduce((best, item) => !best || item.distance_meters < best.distance_meters ? item : best, null);
    for (const [index, item] of items.entries()) {
        const location = item.location;

        const row = document.createElement("div");
        row.className = "location-item";

        if (location.id === selectedLocationId) {
            row.classList.add("selected");
        }

        const info = document.createElement("div");
        info.className = "location-info";

        const title = document.createElement("h3");
        title.textContent = `${index + 1}. ${t(location.name)}`;

        const description = document.createElement("p");
        description.textContent =
            item.distance_meters == null ? (t(location.description_source) || t("Khám phá từ xa")) :
            `${t(dataMode === "demo" ? t("Từ vị trí mẫu") : t("Từ vị trí tìm kiếm"))}: ${Math.round(item.distance_meters)} m`;
        if (nearest === item) {
            const badge = document.createElement("span");
            badge.className = "nearest-badge";
            badge.textContent = t("Gần nhất trong danh sách");
            description.append(" · ", badge);
        }

        const button = document.createElement("button");
        button.type = "button";
        button.className = "location-action";
        button.textContent = location.id === selectedLocationId ? t("Xem bài đang chọn") : t("Thuyết minh");
        button.disabled = !location.is_ready;
        button.setAttribute("aria-pressed", String(location.id === selectedLocationId));

        if (!location.is_ready) {
            button.textContent = t("Chưa sẵn sàng");
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
async function loadNearby(latitude, longitude, remote = false) {
    if (listController) {
        listController.abort();
    }

    const controller = new AbortController();
    listController = controller;
    const version = ++listVersion;
    const requestedMode = remote ? "remote" : explorationMode;

    const params = new URLSearchParams({
        latitude: String(latitude),
        longitude: String(longitude),
        radius: String(SEARCH_RADIUS)
    });

    detectButton.disabled = true;

    try {
        const response = await fetch(
            remote ? "/narration/catalog" : `/narration/nearby?${params.toString()}`,
            { signal: controller.signal }
        );

        if (!response.ok) {
            throw new Error(t("Không thể tải danh sách địa điểm."));
        }

        const data = await response.json();

        if (version !== listVersion) {
            return;
        }

        const previousSelection = selectedLocationId;
        nearbyLocations = data;
        dataMode = requestedMode;
        const retained = selectedItem();
        if (previousSelection !== null && !retained) {
            selectedLocationId = null;
            clearNarration();
        }
        renderLocations();
        updateListHeading();
        if (autoGpsEnabled) {
            autoGpsStatus.textContent = t("Đã cập nhật vị trí. Tự làm mới khi bạn di chuyển.");
        }
        if (retained) {
            updateDistanceInfo(retained.distance_meters);
            if (!narrationController) {
                showStatus(t("Đã cập nhật danh sách. Giữ bài đang chọn: {name}.", { name: t(retained.location.name) }), "success");
            }
        } else {
            showStatus(
                previousSelection !== null ? t("Điểm đang chọn không còn trong kết quả. Hãy chọn một điểm khác.") :
                remote ? t("Có {count} địa điểm để khám phá từ xa.", { count: data.length }) :
                    (data.length ? t("Đã tìm thấy {count} địa điểm trong 500 mét.", { count: data.length }) :
                    t("Bạn đang ở xa các địa điểm đã lưu. Chọn Khám phá từ xa để tiếp tục.")),
                data.length ? "success" : "warning"
            );
        }

        lastSearchPosition = remote ? null : { latitude, longitude };
        lastSearchTime = Date.now();

    } catch (error) {
        if (error.name !== "AbortError" && version === listVersion) {
            if (autoGpsEnabled) {
                autoGpsStatus.textContent = t("Chưa cập nhật được danh sách. Hãy kiểm tra kết nối.");
            }
            showStatus(t("Không thể tải danh sách địa điểm."), "error");
        }
    } finally {
        if (listController === controller) {
            listController = null;
            detectButton.disabled = false;
        }
    }
}


// Người dùng chọn đúng POI muốn nghe
async function selectLocation(item, { force = false, reveal = true } = {}) {
    const location = item.location;
    const selectedLanguage = languageSelect.value;
    const key = `${location.id}:${selectedLanguage}`;
    if (!force && (pendingNarrationKey === key || loadedNarrationKey === key)) {
        locationMap?.focusLocation(location.id);
        if (reveal) revealNarration();
        return;
    }

    clearNarration();

    selectedLocationId = location.id;
    renderLocations();
    locationMap?.focusLocation(location.id);

    resultCard.hidden = false;
    resultCard.setAttribute("aria-busy", "true");
    mapResultLink.hidden = false;
    locationName.textContent = t(location.name);
    updateLocationReference(location);
    languageInfo.textContent = t("Đang tải {language}…", { language: languageNames[selectedLanguage] || selectedLanguage });
    updateDistanceInfo(item.distance_meters);
    narrationText.textContent = t("Đang lấy nội dung…");
    if (reveal) revealNarration();

    const version = narrationVersion;
    const controller = new AbortController();
    narrationController = controller;
    pendingNarrationKey = key;
    let timedOut = false;
    const timer = setTimeout(() => {
        timedOut = true;
        controller.abort();
    }, 8000);

    showStatus(
        t("Đang chuẩn bị thuyết minh: {name}…", { name: t(location.name) })
    );

    try {
        const params = new URLSearchParams({
            language: selectedLanguage
        });

        const response = await fetch(
            `/narration/locations/${location.id}/text?${params}`,
            {
                signal: controller.signal
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(t("Không thể lấy thuyết minh."));
        }

        if (version !== narrationVersion) {
            return;
        }

        loadedNarrationKey = ["success", "text_only"].includes(data.status) ? key : null;
        displayNarration(data, selectedItem()?.distance_meters ?? null);

    } catch (error) {
        if (
            (error.name !== "AbortError" || timedOut) &&
            version === narrationVersion
        ) {
            const message = timedOut ? t("Kết nối quá lâu. Bạn có thể thử tải lại bài.") : t("Không thể lấy thuyết minh.");
            resultCard.setAttribute("aria-busy", "false");
            narrationText.textContent = message;
            languageInfo.textContent = t("Ngôn ngữ: {language}", { language: languageNames[selectedLanguage] || selectedLanguage });
            retryNarrationButton.hidden = false;
            showStatus(message, "error");
        }
    } finally {
        clearTimeout(timer);
        if (narrationController === controller) {
            narrationController = null;
            pendingNarrationKey = null;
        }
    }
}


// Tìm theo tọa độ đang nhập
function searchFromInputs() {
    try {
        const coords = readCoordinates();
        stopAutoGps();
        setMode("coordinates");
        void loadNearby(coords.latitude, coords.longitude);
    } catch (error) {
        showStatus(error.message, "error");
    }
}


// Lấy GPS thiết bị một lần
function getCurrentLocation() {
    if (!navigator.geolocation) {
        showStatus(t("Trình duyệt không hỗ trợ GPS."), "error");
        return;
    }
    stopAutoGps();
    setMode("gps");
    const requestVersion = gpsVersion;

    gpsButton.disabled = true;
    showStatus(t("Đang lấy GPS hiện tại..."));

    navigator.geolocation.getCurrentPosition(
        (position) => {
            if (requestVersion !== gpsVersion) return;
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            latitudeInput.value = latitude.toFixed(6);
            longitudeInput.value = longitude.toFixed(6);

            gpsButton.disabled = false;
            void loadNearby(latitude, longitude);
        },
        (error) => {
            if (requestVersion !== gpsVersion) return;
            setMode(dataMode);
            showStatus(
                t("Không lấy được GPS. Hãy kiểm tra quyền vị trí và thử lại."),
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
            t("GPS chưa đủ chính xác để cập nhật danh sách.");
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
        t("Đang cập nhật danh sách địa điểm...");

    void loadNearby(latitude, longitude);
}


// Bật theo dõi GPS
function startAutoGps() {
    if (!navigator.geolocation) {
        showStatus(t("Thiết bị không hỗ trợ GPS."), "error");
        return;
    }
    setMode("gps");

    autoGpsEnabled = true;
    lastSearchPosition = null;
    lastSearchTime = 0;

    autoGpsButton.textContent = t("Tắt theo dõi GPS");
    autoGpsButton.classList.add("active");
    autoGpsButton.setAttribute("aria-pressed", "true");

    autoGpsStatus.textContent = t("Đang chờ GPS...");

    watchId = navigator.geolocation.watchPosition(
        onPositionChanged,
        (error) => {
            autoGpsStatus.textContent =
                t("Không lấy được GPS. Hãy kiểm tra quyền vị trí và thử lại.");

            if (error.code === 1) {
                stopAutoGps();
                autoGpsStatus.textContent =
                    t("Đã tắt GPS vì chưa được cấp quyền vị trí.");
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

    autoGpsButton.textContent = t("Bật theo dõi GPS");
    autoGpsButton.classList.remove("active");
    autoGpsButton.setAttribute("aria-pressed", "false");

    autoGpsStatus.textContent = t("GPS tự động đã tắt.");
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

// Giữ địa điểm, tải ngay bản ngôn ngữ mới và không tự phát âm thanh.
languageSelect.addEventListener("change", () => {
    window.BatTrangI18n.setLanguage(languageSelect.value);
});
window.addEventListener("visitorlanguagechange", () => {
    // Refresh labels and the selected article; keep GPS, filters and the map view.
    renderLocations();
    updateListHeading();
    refreshModeLabel();
    autoGpsButton.textContent = t(autoGpsEnabled ? "Tắt theo dõi GPS" : "Bật theo dõi GPS");
    autoGpsStatus.textContent = t(autoGpsEnabled ? "Đang chờ GPS..." : "GPS tự động đang tắt.");
    const item = selectedItem();
    if (item) void selectLocation(item, { force: true, reveal: false });
    else showStatus(t("Đã đổi ngôn ngữ. Hãy chọn địa điểm muốn nghe."));
});

retryNarrationButton.addEventListener("click", () => {
    const item = selectedItem();
    if (item) void selectLocation(item, { force: true, reveal: false });
});

function applySearch() {
    renderLocations();
    const count = visibleLocations().length;
    showStatus(t("Hiển thị {count}/{total} địa điểm.", { count, total: nearbyLocations.length }), count ? "success" : "warning");
}
let searchTimer = null;
locationSearch.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(applySearch, 200);
});
clearSearchButton.addEventListener("click", () => {
    clearTimeout(searchTimer);
    locationSearch.value = "";
    applySearch();
    locationSearch.focus();
});

window.addEventListener("pagehide", () => { stopAutoGps(); stopDeviceSpeech(); });


function setMode(mode) {
    explorationMode = mode;
    gpsVersion++;
    gpsButton.disabled = false;
    if (listController) listController.abort();
    listVersion++;
    refreshModeLabel();
}

function refreshModeLabel() {
    const labels = {
        remote: t("Khám phá từ xa — không sử dụng GPS."),
        demo: t("Vị trí mô phỏng tại Bát Tràng — không phải vị trí thiết bị."),
        gps: t("Sử dụng GPS thực tế của thiết bị."),
        coordinates: t("Tìm theo tọa độ nhập thủ công — không phải GPS thiết bị.")
    };
    modeStatus.textContent = labels[explorationMode];
}

function updateListHeading() {
    document.getElementById("listHeading").textContent = dataMode === "remote" ? t("Địa điểm Bát Tràng") : t("Địa điểm xung quanh");
    document.getElementById("listScope").textContent = dataMode === "remote" ? t("Khám phá từ xa") : t("500 mét");
}

async function showAllLocations() {
    clearTimeout(searchTimer);
    locationSearch.value = "";
    stopAutoGps();
    setMode("remote");
    await loadNearby(null, null, true);
    if (explorationMode === "remote" && dataMode === "remote") locationMap?.fitLocations();
}

document.getElementById("catalogButton").addEventListener("click", () => {
    void showAllLocations();
});

document.getElementById("demoButton").addEventListener("click", () => {
    stopAutoGps();
    setMode("demo");
    latitudeInput.value = "20.974974";
    longitudeInput.value = "105.912077";
    void loadNearby(20.974974, 105.912077);
});

if (window.BatTrangMap) {
    locationMap = new window.BatTrangMap(
        (id) => {
            const item = nearbyLocations.find(item => item.location.id === id);
            if (item) void selectLocation(item);
        },
        () => { void showAllLocations(); }
    );
}
void loadNearby(null, null, true);
