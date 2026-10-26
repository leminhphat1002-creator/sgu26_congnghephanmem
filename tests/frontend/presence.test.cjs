const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../../app/static/app/presence.js"), "utf8");

function page({ visibility = "visible", request = async () => ({ status: 204 }) } = {}) {
    const calls = [], intervals = [], events = {}, timers = new Map();
    const context = {
        document: { visibilityState: visibility, addEventListener(name, fn) { events[name] = fn; } },
        window: { addEventListener(name, fn) { events[name] = fn; } },
        AbortController,
        setInterval(fn, delay) { intervals.push({ fn, delay }); },
        setTimeout(fn) { const id = timers.size + 1; timers.set(id, fn); return id; },
        clearTimeout(id) { timers.delete(id); },
        fetch(url, options) { calls.push({ url, options }); return request(url, options); }
    };
    vm.runInNewContext(source, context);
    return { calls, intervals, events, context, timers };
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
