// Voice input (frontend/voice.js) with a mocked Web Speech API and a minimal fake DOM. Run: node --test tests/js
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SOURCE = readFileSync(new URL("../../frontend/voice.js", import.meta.url), "utf8");

class FakeNode {
  constructor(tag) { this.tag = tag; this.attrs = {}; this.dataset = {}; this.children = []; this.listeners = {}; this.value = ""; this.focused = 0; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  appendChild(c) { this.children.push(c); return c; }
  addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); }
  dispatchEvent(e) { (this.listeners[e.type] || []).forEach(fn => fn(e)); }
  click() { (this.listeners.click || []).forEach(fn => fn({})); }
  focus() { this.focused++; }
  get textContent() { return this.children.map(c => (typeof c === "string" ? c : c.textContent)).join(""); }
  set textContent(v) { this.children = v ? [String(v)] : []; }
  find(pred) { for (const c of this.children) { if (typeof c !== "string") { if (pred(c)) return c; const f = c.find(pred); if (f) return f; } } return null; }
}

function env({ api = "std", ua = "Mozilla/5.0 Chrome/156", available, installOk } = {}) {
  const made = [];
  class FakeSR {
    constructor() { this.processLocally = false; made.push(this); this.started = 0; this.stopped = 0; this.aborted = 0; }
    start() { this.started++; }
    stop() { this.stopped++; }
    abort() { this.aborted++; this.onerror?.({ error: "aborted" }); this.onend?.(); }
    // test helpers: simulate what the browser would do
    say(text, isFinal = true) { this.onresult?.({ results: [Object.assign([{ transcript: text }], { isFinal })] }); }
    fail(error) { this.onerror?.({ error }); this.onend?.(); }
    end() { this.onend?.(); }
  }
  if (available !== undefined) { FakeSR.available = async () => available; FakeSR.install = async () => installOk; }
  const winListeners = {}, docListeners = {};
  const ctx = {
    console,
    navigator: { userAgent: ua },
    document: { documentElement: { lang: "en-US" }, hidden: false, addEventListener: (t, fn) => (docListeners[t] ||= []).push(fn) },
    Event: class { constructor(type) { this.type = type; } },
    el(tag, attrs = {}, ...kids) {
      const n = new FakeNode(tag);
      for (const [k, v] of Object.entries(attrs || {})) {
        if (v == null || v === false) continue;
        if (k === "text") n.textContent = v; else if (k === "class") n.className = v;
        else if (k.startsWith("on")) n.addEventListener(k.slice(2), v); else n.setAttribute(k, v);
      }
      kids.flat(Infinity).forEach(c => c != null && c !== false && n.appendChild(c));
      return n;
    },
    put(p, ...kids) { kids.flat(Infinity).forEach(c => c != null && c !== false && p.appendChild(c)); return p; },
    clear(n) { n.children = []; return n; },
  };
  ctx.window = { addEventListener: (t, fn) => (winListeners[t] ||= []).push(fn) };
  if (api === "std") ctx.window.SpeechRecognition = FakeSR;
  if (api === "webkit") ctx.window.webkitSpeechRecognition = FakeSR;
  vm.createContext(ctx);
  vm.runInContext(SOURCE + "\n;globalThis.__setupVoice = setupVoice;", ctx);
  const input = new FakeNode("textarea");
  const voice = ctx.__setupVoice(input);
  const label = () => voice.status.children[0].textContent;
  const msg = () => voice.status.children[2].textContent;
  const fire = (type, target = winListeners) => (target[type] || []).forEach(fn => fn({}));
  return { ctx, voice, input, made, label, msg, fire, winListeners, docListeners, last: () => made[made.length - 1], tick: () => new Promise(r => setImmediate(r)) };
}

test("ready when the API exists; unavailable (unsupported) when it doesn't", () => {
  const a = env();
  assert.equal(a.voice.state(), "ready"); assert.equal(a.label(), "Ready");
  const b = env({ api: "none" });
  assert.equal(b.voice.state(), "unavailable"); assert.equal(b.label(), "Microphone unavailable");
  assert.match(b.msg(), /isn’t supported in this browser/);
  b.voice.button.click();
  assert.equal(b.made.length, 0);
});

test("prefixed webkitSpeechRecognition is used too", () => {
  const e = env({ api: "webkit" }); e.voice.button.click();
  assert.equal(e.made.length, 1); assert.equal(e.voice.state(), "listening");
});

test("click starts listening; recognized speech fills the input and nothing is submitted", () => {
  const e = env(); e.input.value = "Earlier text";
  e.voice.button.click();
  assert.equal(e.label(), "Listening"); assert.equal(e.voice.button.getAttribute("aria-pressed"), "true");
  assert.equal(e.last().started, 1); assert.equal(e.last().lang, "en-US");
  e.last().say("what should I do next", false);
  assert.equal(e.input.value, "Earlier text what should I do next");
  e.last().say("what should I do next");
  // stopping: Processing until the browser ends recognition, then "Transcript ready"
  e.voice.button.click();
  assert.equal(e.voice.state(), "processing"); assert.equal(e.label(), "Processing"); assert.equal(e.last().stopped, 1);
  e.voice.button.click();   // repeated click while processing is ignored
  assert.equal(e.made.length, 1);
  e.last().end();
  assert.equal(e.voice.state(), "ready"); assert.match(e.msg(), /Transcript ready/);
  assert.equal(e.input.value, "Earlier text what should I do next");
  // the user can edit before sending; voice never overwrites it afterwards
  e.input.value += " after the GMAT?";
  assert.equal(e.input.value, "Earlier text what should I do next after the GMAT?");
});

test("a second click while listening stops instead of starting a second recognizer", () => {
  const e = env(); e.voice.button.click(); e.voice.button.click();
  assert.equal(e.made.length, 1); assert.equal(e.last().stopped, 1);
});

for (const [error, state, pattern] of [
  ["not-allowed", "unavailable", /Microphone access is blocked/],
  ["service-not-allowed", "unavailable", /Microphone access is blocked/],
  ["audio-capture", "unavailable", /No microphone was found/],
  ["no-speech", "ready", /didn’t hear anything/],
  ["something-new", "ready", /stopped because of an error/],
]) {
  test(`error "${error}" → ${state}`, () => {
    const e = env(); e.voice.button.click(); e.last().fail(error);
    assert.equal(e.voice.state(), state); assert.match(e.msg(), pattern);
    e.voice.button.click(); assert.equal(e.made.length, 2, "the user can try again");
  });
}

test("network error without local mode → unavailable with the network message", async () => {
  const e = env(); e.voice.button.click(); e.last().fail("network"); await e.tick();
  assert.equal(e.label(), "Microphone unavailable"); assert.match(e.msg(), /temporarily unavailable/);
});

test("network error in Electron or Brave → explains the blocked speech service", async () => {
  const e = env({ ua: "Mozilla/5.0 Chrome/138 Electron/37.0.0" }); e.voice.button.click(); e.last().fail("network"); await e.tick();
  assert.match(e.msg(), /blocks the online speech service/);
});

test("network error with local mode installed → retries locally and keeps using it", async () => {
  const e = env({ available: "available" }); e.voice.button.click(); e.last().fail("network");
  assert.equal(e.label(), "Processing"); await e.tick();
  assert.equal(e.made.length, 2); assert.equal(e.last().processLocally, true); assert.equal(e.voice.state(), "listening");
  e.last().say("local works"); e.voice.button.click(); e.last().end();
  assert.equal(e.input.value, "local works");
  e.voice.button.click(); assert.equal(e.last().processLocally, true, "later clicks go straight to local mode");
});

test("network error with a downloadable local mode → offers a download; success starts local listening", async () => {
  const e = env({ available: "downloadable", installOk: true }); e.voice.button.click(); e.last().fail("network"); await e.tick();
  const btn = e.voice.status.find(n => n.tag === "button");
  assert.ok(btn, "download button shown"); assert.match(e.msg(), /download on-device speech/i);
  btn.click(); assert.equal(e.label(), "Processing"); await e.tick(); await e.tick();
  assert.equal(e.last().processLocally, true); assert.equal(e.voice.state(), "listening");
});

test("failed download → unavailable", async () => {
  const e = env({ available: "downloadable", installOk: false }); e.voice.button.click(); e.last().fail("network"); await e.tick();
  e.voice.status.find(n => n.tag === "button").click(); await e.tick(); await e.tick();
  assert.equal(e.voice.state(), "unavailable");
});

test("closing the chat stops listening but keeps the transcript", () => {
  const e = env(); e.voice.button.click(); e.last().say("keep me");
  e.voice.stop(); assert.equal(e.last().stopped, 1); e.last().end();
  assert.equal(e.input.value, "keep me"); assert.equal(e.voice.state(), "ready");
});

for (const [name, fire] of [["hashchange", e => e.fire("hashchange")], ["pagehide", e => e.fire("pagehide")],
  ["hidden tab", e => { e.ctx.document.hidden = true; e.fire("visibilitychange", e.docListeners); }]]) {
  test(`navigating away (${name}) aborts the microphone`, () => {
    const e = env(); e.voice.button.click(); fire(e);
    assert.equal(e.last().aborted, 1); assert.equal(e.voice.state(), "ready");
  });
}

test("start() throwing (e.g. already started) is handled", () => {
  const e = env(); e.ctx.window.SpeechRecognition.prototype.start = () => { throw new Error("InvalidStateError"); };
  e.voice.button.click(); assert.equal(e.voice.state(), "ready"); assert.match(e.msg(), /stopped because of an error/);
});
