const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const base = path.join(__dirname, "../../app/static/app");
const source = fs.readFileSync(path.join(base, "i18n.js"), "utf8");
const key = "bat-trang-visitor-language-v1";

function element(dataset = {}) {
    return {
        dataset, handlers: {}, attributes: {}, value: "", textContent: "",
        addEventListener(name, handler) { this.handlers[name] = handler; },
        setAttribute(name, value) { this.attributes[name] = value; },
        querySelectorAll() { return []; },
        showModal() { this.open = true; }, close() { this.open = false; }
    };
}
function visitor({ stored = null, languages = ["en-US"], blocked = false } = {}) {
    const store = new Map(stored === null ? [] : [[key, stored]]);
    const choices = ["vi", "en", "ja"].map(code => element({ languageChoice: code }));
    const elements = Object.fromEntries([
        "language", "languageDialog", "visitorCountry", "confirmLanguage",
        "changeLanguageButton", "languagePreferenceStatus"
    ].map(id => [id, element()]));
    elements.languageDialog.querySelectorAll = selector => selector === "[data-language-choice]" ? choices : [];
    const events = [];
    const context = {
        navigator: { languages },
        localStorage: {
            getItem(name) { if (blocked) throw Error("blocked"); return store.get(name) || null; },
            setItem(name, value) { if (blocked) throw Error("blocked"); store.set(name, value); }
        },
        document: { documentElement: {}, querySelectorAll() { return []; }, getElementById(id) { return elements[id]; } },
        CustomEvent: class { constructor(type) { this.type = type; } },
        window: { dispatchEvent(event) { events.push(event.type); } }
    };
    vm.runInNewContext(source, context);
    return { api: context.window.BatTrangI18n, elements, choices, store, events, context };
}

test("first visit suggests a supported browser language and opens the chooser", () => {
    const user = visitor({ languages: ["fr-FR", "ja-JP", "en"] });
    user.api.init();
    assert.equal(user.api.language, "ja");
    assert.equal(user.elements.language.value, "ja");
    assert.equal(user.elements.languageDialog.open, true);
    assert.equal(user.store.size, 0); // A suggestion does not persist without a choice.
    assert.equal(visitor({ languages: ["de-DE"] }).api.language, "en");
});

test("country suggests a language, but a visitor can override it before confirming", () => {
    const user = visitor();
    user.api.init();
    user.elements.visitorCountry.value = "JP";
    user.elements.visitorCountry.handlers.change();
    assert.equal(user.choices[2].attributes["aria-pressed"], "true");
    assert.equal(user.api.language, "en"); // Preview only.
    user.choices[0].handlers.click();
    user.elements.confirmLanguage.handlers.click();
    assert.equal(user.api.language, "vi");
    assert.equal(user.elements.language.value, "vi");
    assert.equal(user.context.document.documentElement.lang, "vi");
    assert.equal(user.elements.languageDialog.open, false);
    assert.deepEqual(JSON.parse(user.store.get(key)), { language: "vi", country: "JP" });
    assert.deepEqual(user.events, ["visitorlanguagechange"]);
});

test("preference survives reload and does not change another visitor's browser", () => {
    const first = visitor();
    first.api.setLanguage("ja", "JP");
    const reload = visitor({ stored: first.store.get(key), languages: ["vi-VN"] });
    reload.api.init();
    assert.equal(reload.api.language, "ja");
    assert.equal(reload.elements.languageDialog.open, undefined);
    assert.equal(visitor({ languages: ["vi-VN"] }).api.language, "vi");
    assert.equal(first.api.setLanguage("__proto__"), false);
    assert.equal(first.api.language, "ja");
});

test("corrupt or blocked browser storage does not prevent language selection", () => {
    assert.equal(visitor({ stored: "{broken" }).api.language, "en");
    assert.equal(visitor({ stored: '{"language":"fr","country":"__proto__"}' }).api.language, "en");
    const user = visitor({ blocked: true });
    user.api.init();
    user.choices[2].handlers.click();
    user.elements.confirmLanguage.handlers.click();
    assert.equal(user.api.language, "ja");
    assert.match(user.elements.languagePreferenceStatus.textContent, /ブラウザー/);
});

test("translation preserves parameters, missing names and user-authored place names", () => {
    const user = visitor();
    assert.equal(user.api.t("Có {count} địa điểm để khám phá từ xa.", { count: 5 }), "5 places to explore remotely.");
    assert.equal(user.api.t(null), "");
    assert.equal(user.api.t("New workshop <script>"), "New workshop <script>");
    user.api.setLanguage("ja");
    assert.equal(user.api.t("Ngôn ngữ: {language}", { language: "日本語" }), "言語：日本語");
});

test("all annotated public labels have English and Japanese translations with matching parameters", () => {
    const catalog = JSON.parse(source.split("const messages = ")[1].split(";\n    const supported")[0]);
    const params = value => [...value.matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort();
    for (const [original, translations] of Object.entries(catalog)) {
        assert.equal(translations.length, 2, original);
        for (const translation of translations) {
            assert.ok(translation.trim(), original);
            assert.deepEqual(params(translation), params(original), original);
        }
    }
    for (const file of ["index.html", "share.html"]) {
        const html = fs.readFileSync(path.join(base, file), "utf8");
        for (const match of html.matchAll(/data-i18n(?:-[\w-]+)?="([^"]+)"/g)) {
            const label = match[1].replaceAll("&quot;", '"').replaceAll("&#x27;", "'").replaceAll("&amp;", "&");
            assert.ok(Object.hasOwn(catalog, label), `${file}: ${label}`);
        }
    }
});
