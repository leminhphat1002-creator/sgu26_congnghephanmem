"use strict";
const mapT = window.BatTrangI18n.t;

// POI come from our catalog, not a geocoding/search service.
window.BatTrangMap = class BatTrangMap {
    constructor(onSelect, onShowAll) {
        this.onSelect = onSelect;
        this.signature = null;
        this.items = [];
        this.geometry = null;
        this.selectedId = null;
        this.markers = new Map();
        this.status = document.getElementById("mapStatus");
        this.count = document.getElementById("mapCount");
        this.notice = document.getElementById("mapNotice");
        this.fitButton = document.getElementById("fitMapButton");
        this.fitButton.addEventListener("click", () => onShowAll());
        if (!window.L) {
            document.getElementById("locationMap").hidden = true;
            this.count.textContent = mapT("Chọn trong danh sách");
            this.notice.hidden = false;
            this.notice.textContent = mapT("Không mở được bản đồ. Bạn vẫn có thể chọn địa điểm trong danh sách bên dưới.");
            return;
        }

        this.map = L.map("locationMap", { scrollWheelZoom: false, maxZoom: 19,
            zoomControl: false, closePopupOnClick: true })
            .setView([20.974974, 105.912077], 16);
        this.map.on("popupopen", () => {
            const close = this.map.getContainer().querySelector(".leaflet-popup-close-button");
            close?.setAttribute("aria-label", mapT("Đóng"));
            close?.setAttribute("title", mapT("Đóng"));
        });
        this.zoomControl = L.control.zoom({ zoomInTitle: mapT("Phóng to"), zoomOutTitle: mapT("Thu nhỏ") }).addTo(this.map);
        window.addEventListener("visitorlanguagechange", () => {
            this.zoomControl.remove();
            this.zoomControl = L.control.zoom({ zoomInTitle: mapT("Phóng to"), zoomOutTitle: mapT("Thu nhỏ") }).addTo(this.map);
            if (!this.notice.hidden) this.loadBackgroundStatus();
        });
        L.control.scale({ imperial: false }).addTo(this.map);
        this.loadBackground();
    }

    async loadBackground() {
        this.notice.hidden = false;
        this.backgroundState = "loading";
        this.loadBackgroundStatus();
        try {
            // A bounded, attributed vector extract ships with the application.
            // No external tile server, API key, or visitor GPS is needed to draw it.
            const response = await fetch("/static/app/bat-trang-basemap.geojson");
            if (!response.ok) throw new Error(`Map HTTP ${response.status}`);
            const data = await response.json();
            if (data.type !== "FeatureCollection" || !data.features?.length || data.bbox?.length !== 4) {
                throw new Error("Invalid local map data");
            }
            const bounds = L.latLngBounds(
                [data.bbox[1], data.bbox[0]], [data.bbox[3], data.bbox[2]]
            );
            this.map.setMaxBounds(bounds);
            const constrainZoom = () => this.map.setMinZoom(this.map.getBoundsZoom(bounds, true));
            constrainZoom();
            this.map.on("resize", constrainZoom);
            this.map.attributionControl.addAttribution(
                '<a href="https://openfreemap.org/">OpenFreeMap</a> · ' +
                '&copy; <a href="https://www.openmaptiles.org/">OpenMapTiles</a> · ' +
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            );
            const renderer = L.canvas({ padding: 0.5 });
            const baseOptions = { interactive: false, renderer };
            const areaColors = {
                landcover: "#dbe6c7", landuse: "#ece5db", park: "#d6e5c3",
                water: "#abd4df", building: "#d9c7b5", waterway: "#98c9d7"
            };
            for (const name of Object.keys(areaColors)) {
                L.geoJSON(data, {
                    ...baseOptions,
                    filter: feature => feature.properties.layer === name,
                    style: { color: areaColors[name], weight: name === "waterway" ? 2 : 0.5,
                        fillColor: areaColors[name], fillOpacity: 1 }
                }).addTo(this.map);
            }
            const roadWidth = feature => {
                const type = feature.properties.class;
                return ["motorway", "trunk", "primary", "secondary", "tertiary"].includes(type) ? 5 : 3;
            };
            for (const outline of [true, false]) {
                L.geoJSON(data, {
                    ...baseOptions,
                    filter: feature => feature.properties.layer === "transportation",
                    style: feature => ({ color: outline ? "#cdbb9f" : "#fffdf7",
                        weight: roadWidth(feature) + (outline ? 2 : 0), opacity: 1 })
                }).addTo(this.map);
            }
            const names = new Set();
            this.roadLabels = L.geoJSON(data, {
                interactive: false,
                filter: feature => {
                    const { layer, name } = feature.properties;
                    if (layer !== "transportation_name" || !name || name.length > 42 || names.has(name)) return false;
                    names.add(name);
                    return true;
                },
                style: { opacity: 0, weight: 0 },
                onEachFeature: (feature, layer) => {
                    const label = document.createElement("span");
                    label.textContent = feature.properties.name;
                    layer.bindTooltip(label, { permanent: true, direction: "center",
                        className: "map-road-label", interactive: false });
                }
            });
            const showLabels = () => {
                if (this.map.getZoom() >= 17) this.roadLabels.addTo(this.map);
                else this.roadLabels.remove();
            };
            showLabels();
            this.map.on("zoomend", showLabels);
            this.backgroundState = "ready";
            this.notice.hidden = true;
        } catch (error) {
            console.error("Local map background unavailable", error);
            this.backgroundState = "error";
            this.loadBackgroundStatus();
        }
    }

    loadBackgroundStatus() {
        this.notice.hidden = this.backgroundState === "ready";
        if (this.backgroundState === "loading") {
            this.notice.textContent = mapT("Đang mở nền bản đồ Bát Tràng…");
        } else if (this.backgroundState === "error") {
            this.notice.textContent = mapT("Chưa mở được nền bản đồ. Bạn vẫn có thể chọn điểm đánh dấu. ");
            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "map-retry";
            retry.textContent = mapT("Tải lại nền bản đồ");
            retry.addEventListener("click", () => this.loadBackground(), { once: true });
            this.notice.append(retry);
        }
    }

    setLocations(items, selectedId) {
        if (!this.map) return;
        const valid = items.filter(item => {
            const { latitude: lat, longitude: lon } = item.location;
            return Number.isFinite(lat) && Number.isFinite(lon) &&
                lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
        });
        const geometry = JSON.stringify(valid.map(item =>
            [item.location.id, item.location.latitude, item.location.longitude]
        ).sort((a, b) => a[0] - b[0]));
        const signature = JSON.stringify([window.BatTrangI18n.language, items.map(item => [item.location, item.distance_meters])]);
        const popupWasOpen = this.markers.get(this.selectedId)?.isPopupOpen();
        const geometryChanged = geometry !== this.geometry;
        if (signature !== this.signature) {
            this.signature = signature;
            this.geometry = geometry;
            this.items = items;
            for (const marker of this.markers.values()) marker.remove();
            this.markers.clear();
            for (const [index, item] of items.entries()) {
                const location = item.location;
                const lat = location.latitude;
                const lon = location.longitude;
                if (!Number.isFinite(lat) || !Number.isFinite(lon) ||
                    lat < -90 || lat > 90 || lon < -180 || lon > 180) continue;
                const icon = L.divIcon({
                    className: "map-pin",
                    html: '<span aria-hidden="true"></span>',
                    iconSize: [38, 44],
                    iconAnchor: [19, 42],
                    popupAnchor: [0, -40]
                });
                const content = document.createElement("div");
                content.className = "map-popup";
                const title = document.createElement("strong");
                title.textContent = mapT(location.name);
                const description = document.createElement("p");
                description.textContent = item.distance_meters == null
                    ? mapT("Chọn điểm để khám phá từ xa.")
                    : mapT("Cách vị trí tìm kiếm {distance} m.", { distance: Math.round(item.distance_meters) });
                content.append(title, description);
                const marker = L.marker([lat, lon], {
                    icon, title: mapT(location.name), keyboard: true, riseOnHover: true
                }).bindPopup(content).addTo(this.map);
                marker.getElement().setAttribute("aria-label", mapT("Chọn {name}", { name: mapT(location.name) }));
                marker.getElement().dataset.number = String(index + 1);
                marker.getElement().addEventListener("keydown", (event) => {
                    if ((event.key === "Enter" || event.key === " ") && !event.repeat) {
                        L.DomEvent.stop(event);
                        this.onSelect(location.id);
                    }
                });
                marker.on("click", () => this.onSelect(location.id));
                this.markers.set(location.id, marker);
            }
            if (geometryChanged) this.fitLocations();
            if (popupWasOpen) this.markers.get(selectedId)?.openPopup();
        }
        this.setSelected(selectedId);
    }

    fitLocations() {
        if (!this.map || this.markers.size === 0) return;
        const bounds = L.latLngBounds([...this.markers.values()].map(marker => marker.getLatLng()));
        this.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17, animate: false });
    }

    setSelected(id) {
        for (const [locationId, marker] of this.markers) {
            const active = locationId === id;
            marker.getElement().classList.toggle("is-selected", active);
            marker.getElement().setAttribute("aria-pressed", String(active));
            marker.setZIndexOffset(active ? 1000 : 0);
        }
        this.count.textContent = mapT("{count} điểm trên bản đồ", { count: this.markers.size });
        if (id !== this.selectedId) this.map.closePopup();
        this.selectedId = id;
        const missing = this.items.length - this.markers.size;
        if (missing) {
            this.count.textContent += mapT(" · {count} điểm chưa có tọa độ", { count: missing });
        }
    }

    focusLocation(id) {
        const marker = this.markers.get(id);
        if (!marker) return;
        if (!this.map.getBounds().contains(marker.getLatLng())) {
            this.map.panTo(marker.getLatLng());
        }
        marker.openPopup();
    }
};
