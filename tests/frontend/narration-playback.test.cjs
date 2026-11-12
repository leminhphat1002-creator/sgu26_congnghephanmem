const { test } = require("node:test");
const assert = require("node:assert/strict");
const { webcrypto } = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../../app/static/app/script.js"), "utf8");
const flush = () => new Promise(resolve => setImmediate(resolve));

function visitor({ playResponses = [] } = {}) {
    const calls = [];
    const elements = new Map();
    const gps = { cancelled: [] };
    const article = {
        status: "success", location_id: 7, location_name: "Chợ gốm",
        narration_title: "A guide to the market", text: "An English guide.",
        requested_language: "ja", content_language: "en", fallback_used: true,
        stream_url: "/narration/locations/7/speech?language=ja&version=old"
    };
    let textStatus = 200;

    function makeElement() {
        return {
            hidden: true, disabled: false, value: "", paused: true, ended: false,
            listeners: new Map(), attributes: new Map(),
            classList: { add() {}, remove() {} },
            addEventListener(name, listener) { this.listeners.set(name, listener); },
            emit(name) { return this.listeners.get(name)?.(); },
            setAttribute(name, value) { this.attributes.set(name, value); },
            removeAttribute(name) { this.attributes.delete(name); },
            hasAttribute(name) { return this.attributes.has(name); },
            set src(url) {
                this.setAttribute("src", url);
                calls.push({ url, method: "MEDIA" });
            },
            set lang(language) { this.setAttribute("lang", language); },
            play() { this.ended = false; this.paused = false; this.emit("play"); return Promise.resolve(); },
            pause() { this.paused = true; this.emit("pause"); },
            load() {}, focus() {}, scrollIntoView() {}, replaceChildren() {}, append() {}, appendChild() {}
        };
    }

    function get(id) {
        if (!elements.has(id)) elements.set(id, makeElement());
        return elements.get(id);
    }

    get("language").value = "ja";
    const context = vm.createContext({
        window: {
            addEventListener() {},
            BatTrangI18n: { t: value => value, init() {}, names: { en: "English", ja: "日本語" } }
        },
        document: { getElementById: get, createElement: makeElement },
        navigator: {
            geolocation: {
                getCurrentPosition(_success, failure) { gps.denyOnce = failure; },
                watchPosition(_success, failure) { gps.denyWatch = failure; return 10; },
                clearWatch(id) { gps.cancelled.push(id); }
            }
        },
        crypto: webcrypto, URL, URLSearchParams, AbortController, setTimeout, clearTimeout,
        async fetch(url, options = {}) {
            calls.push({ url, method: options.method || "GET", body: options.body });
            if (url.endsWith("/play")) {
                const response = playResponses.shift() ?? 204;
                if (response instanceof Error) throw response;
                return { status: response };
            }
            if (url === "/narration/catalog") {
                return {
                    ok: true,
                    json: async () => [{ location: { id: 7, name: "Chợ gốm", is_ready: true } }]
                };
            }
            return { ok: textStatus === 200, status: textStatus, json: async () => ({ ...article }) };
        }
    });
    vm.runInContext(source, context);
    return {
        get, calls, gps, article,
        setTextStatus(status) { textStatus = status; },
        openArticle() { return vm.runInContext("selectLocation(nearbyLocations[0])", context); }
    };
}

test("first Play and replay count once each, while resume does not count", async () => {
    const page = visitor();
    await flush();
    await page.openArticle();

    const player = page.get("audioPlayer");
    const playButton = page.get("playAudioButton");
    const playCalls = () => page.calls.filter(call => call.url.endsWith("/play"));
    assert.equal(page.get("narrationTitle").textContent, "A guide to the market");
    assert.equal(page.get("narrationTitle").attributes.get("lang"), "en");
    assert.equal(page.get("narrationText").attributes.get("lang"), "en");
    assert.equal(playButton.hidden, false);
    assert.equal(player.hasAttribute("src"), false);
    assert.equal(page.calls.some(call => call.url.includes("/speech") || call.url.endsWith("/play")), false);

    playButton.emit("click");
    playButton.emit("click");
    assert.equal(player.attributes.get("src"), page.article.stream_url);
    assert.equal(playCalls().length, 1);

    player.pause();
    await player.play();
    assert.equal(playCalls().length, 1);

    player.ended = true;
    player.emit("ended");
    await player.play();
    const requests = playCalls();
    assert.equal(requests.length, 2);
    assert.ok(requests.every(call => call.method === "POST"));
    const ids = requests.map(call => JSON.parse(call.body).play_id);
    assert.notEqual(ids[0], ids[1]);
    for (const id of ids) assert.match(id, /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/);
});

test("audio recovery reloads the article and does not count a second request", async () => {
    const page = visitor();
    await flush();
    await page.openArticle();
    const player = page.get("audioPlayer");
    const retry = page.get("retryAudioButton");
    const playButton = page.get("playAudioButton");
    playButton.emit("click");
    player.emit("error");
    assert.equal(retry.hidden, false);
    assert.equal(player.hasAttribute("src"), false);

    page.setTextStatus(503);
    retry.emit("click");
    await flush();
    assert.equal(page.get("narrationText").textContent, "An English guide.");
    assert.equal(retry.disabled, false);
    assert.equal(retry.hidden, false);

    page.setTextStatus(200);
    page.article.text = "The updated guide.";
    page.article.stream_url = "/narration/locations/7/speech?language=ja&version=new";
    retry.emit("click");
    await flush();
    assert.equal(page.get("narrationText").textContent, "The updated guide.");
    assert.equal(player.hasAttribute("src"), false);
    assert.equal(retry.hidden, true);

    playButton.emit("click");
    assert.equal(player.attributes.get("src"), page.article.stream_url);
    assert.equal(page.calls.filter(call => call.method === "POST").length, 1);
});

test("transient play counter errors retry once with the same request while audio plays", async () => {
    for (const failure of [new Error("offline"), 503]) {
        const page = visitor({ playResponses: [failure, 204] });
        await flush();
        await page.openArticle();
        page.get("playAudioButton").emit("click");
        assert.equal(page.get("audioPlayer").paused, false);
        await new Promise(resolve => setTimeout(resolve, 800));
        const requests = page.calls.filter(call => call.url.endsWith("/play"));
        assert.equal(requests.length, 2);
        assert.deepEqual(requests[0], requests[1]);
    }
});

test("an unavailable article shows a distinct message and never exposes Play", async () => {
    const page = visitor();
    await flush();
    page.setTextStatus(404);
    await page.openArticle();
    assert.equal(page.get("narrationText").textContent, "Bài thuyết minh không khả dụng.");
    assert.equal(page.get("playAudioButton").hidden, true);
    assert.equal(page.get("retryNarrationButton").hidden, false);
});

test("GPS refusal keeps remote browsing available without sending coordinates", async () => {
    const page = visitor();
    await flush();
    page.get("gpsButton").emit("click");
    page.gps.denyOnce({ code: 1 });
    assert.match(page.get("statusMessage").textContent, /Khám phá từ xa/);
    assert.equal(page.get("gpsButton").disabled, false);

    page.get("autoGpsButton").emit("click");
    page.gps.denyWatch({ code: 1 });
    assert.match(page.get("statusMessage").textContent, /Khám phá từ xa/);
    assert.deepEqual(page.gps.cancelled, [10]);
    assert.deepEqual(page.calls.map(call => call.url), ["/narration/catalog"]);
    await page.openArticle();
    assert.equal(page.get("narrationText").textContent, "An English guide.");
});
