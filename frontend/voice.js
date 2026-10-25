/* Optional voice input for Ask AdmitCompass (loaded before app.js; uses its el/put/clear helpers at call time).

   Mechanism: the browser's Web Speech API (SpeechRecognition / webkitSpeechRecognition) only. Nothing is requested until
   the user clicks the microphone; the browser then asks for permission. The transcript goes into the question box for
   review and editing and is never sent automatically. AdmitCompass never receives, sends or stores audio.

   Where speech is processed is decided by the browser: Chrome and Edge normally send the audio to their vendor's online
   speech service (Google, Microsoft). When that service fails ("network"), newer Chrome can recognize speech in its
   local mode (processLocally), after a one-time language download that the user starts.

   States shown to the user: Ready · Listening · Processing · Microphone unavailable. */
const VOICE_LABEL = { ready: "Ready", listening: "Listening", processing: "Processing", unavailable: "Microphone unavailable" };
const VOICE_MSG = {
  ready: "Click the microphone and speak. Your words appear here to edit before you send.",
  listening: "Speak your question, then click the microphone to stop. Your browser's speech service (Google's in Chrome, Microsoft's in Edge) turns the audio into text; AdmitCompass only receives the text you choose to send.",
  "listening-local": "Speak your question, then click the microphone to stop. Your browser was asked to recognize speech on this device.",
  stopping: "Finishing the transcript…",
  done: "Transcript ready. Review or edit your question, then press Send.",
  unsupported: "Voice input isn’t supported in this browser. Type your question instead.",
  "not-allowed": "Microphone access is blocked. Allow it in your browser settings, or type your question instead.",
  "service-not-allowed": "Microphone access is blocked. Allow it in your browser settings, or type your question instead.",
  "audio-capture": "No microphone was found. Check that one is connected and allowed, or type your question instead.",
  "no-speech": "I didn’t hear anything. Try again or type your question.",
  network: "Voice input is temporarily unavailable. Type your question instead. If this keeps happening, try Chrome.",
  "network-blocked": "This browser blocks the online speech service that voice input needs. Open AdmitCompass in Chrome, Edge or Safari, or type your question instead.",
  "offer-local": "Your browser’s online speech service can’t be reached. You can download on-device speech recognition once (your browser downloads a language pack) and dictate without it.",
  downloading: "Downloading on-device speech… this can take a minute. You can keep typing meanwhile.",
  checking: "The speech service didn’t respond. Checking for on-device speech…",
  error: "Voice input stopped because of an error. Try the microphone again, or type your question.",
};
/* Which errors mean the microphone can't be used right now (vs. a one-off "try again"). */
const VOICE_UNAVAILABLE = new Set(["unsupported", "not-allowed", "service-not-allowed", "audio-capture", "network", "network-blocked"]);
const speechAPI = () => window.SpeechRecognition || window.webkitSpeechRecognition || null;
/* Browsers known to block the online speech service behind webkitSpeechRecognition (it then fails with "network"). */
const speechServiceBlocked = () => !!navigator.brave || /\bElectron\//.test(navigator.userAgent);
/* Local recognition (newer Chrome): feature-detected; "available" | "downloadable" | "downloading" | "unavailable". */
async function onDeviceSpeech(SR, lang) {
  if (!SR || typeof SR.available !== "function") return "unavailable";
  try { return await SR.available({ langs: [lang], processLocally: true }); } catch { return "unavailable"; }
}
function setupVoice(input) {
  let rec = null, state = "ready", base = "", preferLocal = false, gotText = false;
  const lang = () => document.documentElement.lang || "en-US";
  const label = el("span", { class: "cp-voice-state" });
  const msg = el("span", { class: "cp-voice-msg" });
  const status = el("div", { class: "cp-voice", role: "status", "aria-live": "polite" }, label, " ", msg);
  const button = el("button", { type: "button", class: "cp-mic", "aria-pressed": "false", onclick: () => toggle() },
    el("span", { "aria-hidden": "true", class: "cp-mic-ic", text: "🎙" }));
  /* next: ready | listening | processing | unavailable; key: which message to show; action: optional button */
  const set = (next, key = next, action = null) => {
    state = next;
    button.dataset.state = next;
    button.setAttribute("aria-pressed", next === "listening" ? "true" : "false");
    const aria = next === "listening" ? "Stop voice input" : next === "processing" ? "Voice input is processing" : "Start voice input";
    button.setAttribute("aria-label", aria); button.title = aria;
    if (next === "processing") button.setAttribute("aria-disabled", "true"); else button.removeAttribute("aria-disabled");
    label.textContent = VOICE_LABEL[next] || "";
    put(clear(msg), VOICE_MSG[key] ?? VOICE_MSG.error, action ? [" ", action] : null);
  };
  const fail = key => set(VOICE_UNAVAILABLE.has(key) ? "unavailable" : "ready", key);
  const write = text => {   // into the question box, then let the box resize itself; never submits
    input.value = (base && text ? `${base} ` : base) + text;
    input.dispatchEvent(new Event("input"));
  };
  function start(local = preferLocal) {
    const SR = speechAPI();
    if (!SR) { fail("unsupported"); return; }
    if (rec) return;   // already running: a second click must not start a second recognizer
    try {
      rec = new SR();
      rec.lang = lang();
      rec.interimResults = true; rec.continuous = true; rec.maxAlternatives = 1;
      if (local && "processLocally" in rec) rec.processLocally = true;
      base = input.value.trim(); gotText = false;
      const mine = rec;
      rec.onresult = e => {
        if (mine !== rec) return;
        if (local) preferLocal = true;   // local mode worked: keep using it
        let finalText = "", interim = "";
        for (let i = 0; i < e.results.length; i++) (e.results[i].isFinal ? (finalText += e.results[i][0].transcript) : (interim += e.results[i][0].transcript));
        const text = `${finalText}${interim}`.replace(/\s+/g, " ").trim();
        if (text) gotText = true;
        write(text);
      };
      rec.onerror = e => {
        if (mine !== rec) return;
        rec = null;
        if (e.error === "aborted") { set("ready"); return; }
        if (e.error === "network" && !local) { onNetworkError(); return; }
        fail(e.error in VOICE_MSG ? e.error : "error");
      };
      rec.onend = () => {
        if (mine !== rec) return;   // an error handler already took over
        rec = null;
        set("ready", gotText ? "done" : (state === "listening" || state === "processing") ? "no-speech" : "ready");
        input.focus();
      };
      rec.start();   // the browser asks for microphone permission here, after the click
      set("listening", local ? "listening-local" : "listening");
    } catch { rec = null; fail("error"); }
  }
  /* The online speech service failed: try the browser's local mode before giving up. */
  async function onNetworkError() {
    set("processing", "checking");
    const SR = speechAPI(), avail = await onDeviceSpeech(SR, lang());
    if (avail === "available") { start(true); return; }
    if (avail === "downloadable" || avail === "downloading") {
      const dl = el("button", { type: "button", class: "linkbtn cp-voice-act", text: "Download on-device speech",
        onclick: async () => {
          set("processing", "downloading");
          let ok = false;
          try { ok = await SR.install({ langs: [lang()], processLocally: true }); } catch { ok = false; }
          if (ok) start(true); else fail(speechServiceBlocked() ? "network-blocked" : "network");
        } });
      set("unavailable", "offer-local", dl);
      return;
    }
    fail(speechServiceBlocked() ? "network-blocked" : "network");
  }
  /* Stop listening and keep what was heard (close the chat, click the microphone again). */
  function stop() {
    if (!rec) return;
    set("processing", "stopping");
    try { rec.stop(); } catch { rec = null; set("ready"); }
  }
  /* Drop everything immediately (navigating away, leaving the page). */
  function abort() {
    if (!rec) return;
    const r = rec; rec = null;
    try { r.abort(); } catch { /* already stopped */ }
    set("ready");
  }
  function toggle() {
    if (state === "processing") return;   // ignore repeated clicks while finishing or checking
    if (!speechAPI()) { fail("unsupported"); return; }
    rec ? stop() : start();
  }
  window.addEventListener("hashchange", abort);
  window.addEventListener("pagehide", abort);
  document.addEventListener("visibilitychange", () => { if (document.hidden) abort(); });
  if (speechAPI()) set("ready"); else set("unavailable", "unsupported");
  return { button, status, stop, abort, state: () => state };
}
