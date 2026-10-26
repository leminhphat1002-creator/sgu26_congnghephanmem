const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../../app/static/admin/script.js"), "utf8");
const settle = () => new Promise(resolve => setImmediate(resolve));

async function admin() {
    const nodes = new Map(), intervals = new Map(), timers = new Map(), events = {};
    let reply = { active_visitors: 2 };
    const calls = [];
    const node = id => {
        if (!nodes.has(id)) nodes.set(id, {
            hidden: false, value: "", textContent: "", classList: { toggle() {} },
            addEventListener() {}
        });
        return nodes.get(id);
    };
    const context = {
        document: {
            visibilityState: "visible", getElementById: node, querySelectorAll: () => [],
            addEventListener(name, fn) { events[name] = fn; }
        },
        window: { addEventListener(name, fn) { events[name] = fn; } },
        AbortController,
        setInterval(fn, delay) { const id = {}; intervals.set(id, { fn, delay }); return id; },
        clearInterval(id) { intervals.delete(id); },
        setTimeout(fn) { const id = {}; timers.set(id, fn); return id; },
        clearTimeout(id) { timers.delete(id); },
        async fetch(url, options) {
            if (url === "/api/admin/me") return { status: 401, ok: false, json: async () => ({}) };
            calls.push({ url, options });
            if (reply instanceof Error) throw reply;
            return { status: reply.status || 200, ok: !reply.status, json: async () => reply };
        }
    };
    vm.runInNewContext(source, context);
    await settle();
    node("adminView").hidden = false;
    return { context, node, calls, intervals, timers, events, reply(value) { reply = value; } };
}

test("admin polls presence every 15 seconds and stops when logged out or hidden", async () => {
    const page = await admin();
    page.context.startPresencePolling();
    await settle();
    assert.equal(page.node("activeVisitorsCount").textContent, "2");
    assert.equal(page.intervals.size, 1);
    const tick = [...page.intervals.values()][0];
    assert.equal(tick.delay, 15000);
    page.reply({ active_visitors: 3 });
    tick.fn();
    await settle();
    assert.equal(page.node("activeVisitorsCount").textContent, "3");
    assert.ok(page.calls.every(call => call.url === "/api/admin/presence"));
    page.context.document.visibilityState = "hidden";
    const before = page.calls.length;
    tick.fn();
    assert.equal(page.calls.length, before);
    page.context.showLogin();
    assert.equal(page.intervals.size, 0);
    assert.equal(page.timers.size, 0);
});

test("admin marks failed readings unknown, recovers, and stops after a 401", async () => {
    const page = await admin();
    page.reply(new Error("offline"));
    page.context.startPresencePolling();
    await settle();
    assert.equal(page.node("activeVisitorsCount").textContent, "—");
    page.reply({ active_visitors: 0 });
    await page.context.refreshPresence();
    assert.equal(page.node("activeVisitorsCount").textContent, "0");
    page.reply({ status: 401 });
    await page.context.refreshPresence();
    assert.equal(page.node("adminView").hidden, true);
    assert.equal(page.intervals.size, 0);
    assert.equal(page.timers.size, 0);
});
