const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../../app/static/app/presence.js"), "utf8");

function page({ visibility = "visible", request = async () => ({ status: 204, ok: true }), geolocation } = {}) {
    const calls = [], intervals = [], events = {}, timers = new Map();
    const share = { checked: false, addEventListener(name, fn) { events[name] = fn; } };
    const status = { dataset: {} };
    const context = {
        document: { visibilityState: visibility, addEventListener(name, fn) { events[name] = fn; },
            getElementById(id) { return id === "shareVisitorLocation" ? share : status; } },
        window: { BatTrangI18n: { t: text => text }, addEventListener(name, fn) { events[name] = fn; } },
        navigator: { geolocation },
        AbortController,
        setInterval(fn, delay) { intervals.push({ fn, delay }); },
        setTimeout(fn) { const id = timers.size + 1; timers.set(id, fn); return id; },
        clearTimeout(id) { timers.delete(id); },
        fetch(url, options) { calls.push({ url, options }); return request(url, options); }
    };
    vm.runInNewContext(source, context);
    return { calls, intervals, events, context, timers, share, status };
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test("visitor sends credentialed heartbeat every 30 seconds without location or identity data", async () => {
    const user = page();
    await settle();
    assert.equal(user.calls.length, 1);
    assert.equal(user.calls[0].url, "/api/presence/heartbeat");
    assert.equal(user.calls[0].options.method, "POST");
    assert.equal(user.calls[0].options.credentials, "same-origin");
    assert.equal(user.calls[0].options.body, undefined);
    assert.equal(user.intervals[0].delay, 30000);
    user.intervals[0].fn();
    await settle();
    assert.equal(user.calls.length, 2);
    assert.equal(user.timers.size, 0);
});

test("background tabs stop heartbeats and resume when visible", async () => {
    const user = page({ visibility: "hidden" });
    user.intervals[0].fn();
    assert.equal(user.calls.length, 0);
    user.context.document.visibilityState = "visible";
    user.events.visibilitychange();
    await settle();
    assert.equal(user.calls.length, 1);
    user.context.document.visibilityState = "hidden";
    user.events.visibilitychange();
    user.intervals[0].fn();
    assert.equal(user.calls.length, 1);
});

test("pending heartbeats do not overlap and a network error can recover", async () => {
    let rejectRequest;
    const user = page({ request: () => new Promise((_, reject) => { rejectRequest = reject; }) });
    user.events.online();
    user.events.pageshow();
    assert.equal(user.calls.length, 1);
    rejectRequest(new Error("offline"));
    await settle();
    user.intervals[0].fn();
    assert.equal(user.calls.length, 2);
    rejectRequest(new Error("offline"));
    await settle();
    assert.equal(user.timers.size, 0);
});

test("location is rounded and sent only after opt-in, and opt-out explicitly clears it", async () => {
    let requests = 0;
    const user = page({ geolocation: { getCurrentPosition(success) {
        requests++;
        success({ coords: { latitude: 20.974974, longitude: 105.912077 } });
    } } });
    await settle();
    assert.equal(requests, 0);
    user.share.checked = true;
    user.events.change();
    await settle();
    assert.equal(requests, 1);
    assert.deepEqual(JSON.parse(user.calls[1].options.body), { location: { latitude: 20.975, longitude: 105.912 } });
    assert.match(user.status.textContent, /Đang chia sẻ/);
    user.share.checked = false;
    user.events.change();
    await settle();
    assert.deepEqual(JSON.parse(user.calls[2].options.body), { location: null });
    user.intervals[0].fn();
    await settle();
    assert.equal(requests, 1);
    assert.equal(user.calls[3].options.body, undefined);
});

test("a GPS fix arriving after opt-out is discarded", async () => {
    let positionFound;
    const user = page({ geolocation: { getCurrentPosition(success) { positionFound = success; } } });
    await settle();
    user.share.checked = true;
    user.events.change();
    user.share.checked = false;
    user.events.change();
    positionFound({ coords: { latitude: 20, longitude: 105 } });
    await settle();
    assert.equal(user.calls.length, 2);
    assert.deepEqual(JSON.parse(user.calls[1].options.body), { location: null });
    assert.equal(user.status.hidden, true);
});
