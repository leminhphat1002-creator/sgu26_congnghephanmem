const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../../app/static/admin/script.js"), "utf8");
const settle = () => new Promise(resolve => setImmediate(resolve));

async function admin(overrides = {}) {
    const nodes = new Map(), intervals = new Map(), timers = new Map(), events = {};
    const replies = new Map(Object.entries(overrides));
    let reply = { active_visitors: 2 };
    const calls = [];
    const makeElement = () => ({
        hidden: false, value: "", textContent: "", style: {}, children: [], handlers: {},
        classList: { toggle() {} },
        addEventListener(name, handler) { this.handlers[name] = handler; },
        append(...children) { this.children.push(...children); },
        replaceChildren() { this.children = []; },
        querySelector(selector) {
            return this.children.find(child => child.className === selector.slice(1));
        },
        setAttribute() {}
    });
    const node = id => {
        if (!nodes.has(id)) nodes.set(id, makeElement());
        return nodes.get(id);
    };
    node("adminView").hidden = true;
    const context = {
        document: {
            visibilityState: "visible", getElementById: node, querySelectorAll: () => [],
            createElement: makeElement,
            addEventListener(name, fn) { events[name] = fn; }
        },
        window: { addEventListener(name, fn) { events[name] = fn; } },
        AbortController, URL,
        setInterval(fn, delay) { const id = {}; intervals.set(id, { fn, delay }); return id; },
        clearInterval(id) { intervals.delete(id); },
        setTimeout(fn) { const id = {}; timers.set(id, fn); return id; },
        clearTimeout(id) { timers.delete(id); },
        async fetch(url, options) {
            if (url !== "/api/admin/me") calls.push({ url, options });
            const data = replies.get(url) ?? (url === "/api/admin/me" ? { status: 401 } : reply);
            if (data instanceof Error) throw data;
            return { status: data.status || 200, ok: !data.status, json: async () => data };
        }
    };
    vm.runInNewContext(source, context);
    await settle();
    if (!replies.has("/api/admin/me")) {
        vm.runInNewContext("csrfToken = 'session'", context);
        node("adminView").hidden = false;
    }
    return {
        context, node, calls, intervals, timers, events,
        reply(value) { reply = value; },
        respond(url, value) { replies.set(url, value); }
    };
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

test("admin can see active anonymous sessions and only opted-in map locations", async () => {
    const page = await admin();
    page.reply({ active_visitors: 2, sessions: [
        { id: "guest-one", last_seen_seconds_ago: 3, location: { latitude: 20.975, longitude: 105.912 } },
        { id: "guest-two", last_seen_seconds_ago: 9, location: null }
    ] });
    await page.context.refreshPresence();
    const [shared, unshared] = page.node("presenceBody").children;
    assert.equal(shared.children[0].textContent, "guest-one");
    assert.equal(shared.children[1].textContent, "3 giây trước");
    assert.match(shared.children[2].children[0].href, /openstreetmap\.org.*20\.975/);
    assert.equal(unshared.children[2].textContent, "Chưa chia sẻ vị trí");
    assert.equal(page.node("presenceTable").hidden, false);
    page.context.showLogin();
    assert.equal(page.node("presenceBody").children.length, 0);
    assert.equal(page.node("presenceTable").hidden, true);
});

test("dashboard errors retain the restored session and refresh independently of the location list", async () => {
    const page = await admin({
        "/api/admin/me": { csrf_token: "session", username: "manager" },
        "/api/admin/dashboard": { status: 503 },
        "/api/admin/locations": [],
        "/api/share": { url: "https://guide.example/" }
    });
    assert.equal(page.node("loginView").hidden, true);
    assert.equal(page.node("adminView").hidden, false);
    assert.equal(page.node("dashboardContent").hidden, true);
    assert.equal(page.node("dashboardError").hidden, false);
    assert.match(page.node("dashboardError").textContent, /Làm mới/);
    assert.equal(page.node("locationsBody").children.length, 1);

    page.respond("/api/admin/dashboard", {
        locations: 5, published: 5, narrations: 15, active_visitors: 2, requests_today: 8,
        audio_files: 2, audio_bytes: 1000, daily: [], languages: {}, recent_activity: []
    });
    await page.node("refreshButton").handlers.click();
    assert.equal(page.node("dashboardError").hidden, true);
    assert.equal(page.node("dashboardContent").hidden, false);
    assert.equal(page.node("stats").children[3].children[0].textContent, "YÊU CẦU PHÁT HÔM NAY");

    page.respond("/api/admin/dashboard", new Error("offline"));
    await page.node("refreshButton").handlers.click();
    assert.equal(page.node("dashboardContent").hidden, false);
    assert.match(page.node("dashboardError").textContent, /số liệu lần tải trước/);
    page.respond("/api/admin/dashboard", { status: 401 });
    await page.node("refreshButton").handlers.click();
    assert.equal(page.node("adminView").hidden, true);
    assert.match(page.node("loginMessage").textContent, /hết hiệu lực/);
});

test("transient session probe failure allows retry while an unauthorized response shows normal login", async () => {
    const page = await admin({ "/api/admin/me": new Error("offline") });
    assert.equal(page.node("adminView").hidden, true);
    assert.equal(page.node("restoreSessionButton").hidden, false);
    assert.match(page.node("loginMessage").textContent, /Không kiểm tra được phiên/);
    page.respond("/api/admin/me", { status: 401 });
    await page.node("restoreSessionButton").handlers.click();
    assert.equal(page.node("restoreSessionButton").hidden, true);
    assert.equal(page.node("loginMessage").textContent, "");
});
