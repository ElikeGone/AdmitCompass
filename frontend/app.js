/* AdmitCompass 2.0 single-page app. Plain JS, no build step.
   SECURITY: all server/model text is inserted with textContent (via el()); never as raw HTML. */
"use strict";

const $main = document.getElementById("main");
const AGENTS = [
  { id: "pathway_matcher", name: "Pathway Matcher", desc: "Turns your goal into target roles and a shortlist built on career fit, not prestige." },
  { id: "evidence_analyst", name: "Evidence Analyst", desc: "Checks cost, STEM status, outcomes and sponsorship against official sources." },
  { id: "strategy_planner", name: "Strategy Planner", desc: "Plans your tests, closes your gaps and sizes a weekly plan to your time." },
  { id: "skeptic", name: "Skeptic", desc: "Challenges weak evidence, budget assumptions and immigration overstatements." },
];
const AGENT_NAME = Object.fromEntries(AGENTS.map(a => [a.id, a.name]).concat([["orchestrator", "Orchestrator (code)"]]));
const SCHOOL = { "yale-som-mba": "Yale SOM", "hbs-mba": "HBS", "mit-sloan-mba": "MIT Sloan", "chicago-booth-mba": "Chicago Booth",
  "duke-fuqua-mba": "Duke Fuqua", "rice-jones-mba": "Rice Jones" };
const LABEL_TEXT = { verified_fact: "Verified", inference: "Inference", advice: "Advice", unknown: "Unknown", cited: "From sources" };
const S = { config: null, draft: loadDraft(), step: 0, result: null, poll: null, explore: { q: "", tier: "", state: "", stem: false, max: "", sort: "relevance" } };

/* ---------------- safe DOM helpers ---------------- */
function el(tag, attrs, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = typeof v === "string" ? moneyText(v) : v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)) {
    if (c == null || c === false) continue;
    n.appendChild(c instanceof Node ? c : document.createTextNode(moneyText(String(c))));
  }
  return n;
}
/* Model prose sometimes writes "$91892"; show every bare dollar amount with thousands separators ("$91,892"). */
const moneyText = s => s.replace(/\$(\d{4,})(?![\d,])/g, (_, d) => "$" + Number(d).toLocaleString("en-US"));
const clear = n => { while (n.firstChild) n.removeChild(n.firstChild); return n; };
/* Append children with el()'s rules: flatten arrays, skip null/false, text as text nodes. Use instead of Node.append. */
function put(parent, ...kids) {
  for (const c of kids.flat(Infinity)) if (c != null && c !== false) parent.appendChild(c instanceof Node ? c : document.createTextNode(moneyText(String(c))));
  return parent;
}
const fmtInt = v => (v == null ? "—" : Number(v).toLocaleString("en-US"));
const fmtUSD = v => (v == null ? "—" : "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 }));
const num = v => (v === "" || v == null || Number.isNaN(Number(v)) ? null : Number(v));
function toast(msg) { const t = el("div", { class: "toast", role: "status", text: msg }); document.body.appendChild(t); setTimeout(() => t.remove(), 3500); }
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (opts.method && opts.method !== "GET" && S.csrf) headers["X-CSRF-Token"] = S.csrf;
  const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), opts.timeoutMs || 30000);
  let r;
  try { r = await fetch(path, { credentials: "same-origin", signal: ctrl.signal, ...opts, headers }); }
  catch (e) { const err = new Error(e.name === "AbortError" ? "The server took too long to respond. Please try again." : "Couldn't reach the server. Check your connection and try again."); err.status = 0; throw err; }
  finally { clearTimeout(timer); }
  let body = null;
  try { body = await r.json(); } catch { /* non-JSON */ }
  if (!r.ok) {
    const d = body && body.detail;
    const e = new Error(typeof d === "string" ? d : d && d.message ? d.message : r.status === 422 ? "Some fields are invalid." : `Request failed (${r.status})`);
    e.status = r.status; e.fields = d && d.fields; throw e;
  }
  return body;
}
function extLink(url, text) {
  return typeof url === "string" && /^https:\/\//i.test(url)
    ? el("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: text || url }) : el("span", { class: "muted", text: text || "no link" });
}
function splitLabel(text) {
  const m = /^(verified_fact|inference|advice|unknown)\s*:\s*/i.exec(text || "");
  return m ? [m[1].toLowerCase(), text.slice(m[0].length)] : [null, text || ""];
}
/* Model free text prefixed "verified_fact" is not an evidence-linked claim: show it as "From sources". */
const textLabel = l => (l === "verified_fact" ? "cited" : l);
const labelEl = l => el("span", { class: `label label-${l}`, text: LABEL_TEXT[l] || l });
function note(kind, title, body) { return el("div", { class: `note ${kind || ""}` }, title ? el("b", { text: title + " " }) : null, body); }
function more(summary, ...inner) { return el("details", { class: "more" }, el("summary", { text: summary }), el("div", { class: "inner" }, inner)); }

/* ---------------- draft profile (sessionStorage only) ---------------- */
function loadDraft() {
  try { return JSON.parse(sessionStorage.getItem("ac-draft")) || { budget_period: "year", preferred_us_states: [] }; }
  catch { return { budget_period: "year", preferred_us_states: [] }; }
}
function saveDraft() { sessionStorage.setItem("ac-draft", JSON.stringify(S.draft)); }
function draftFromProfile(p, source) {
  const e = (p.education || [])[0] || {};
  return { source, pristine: true, is_fictional: !!p.is_fictional, citizenship_country: p.citizenship_country || "",
    needs_us_work_authorization: p.needs_us_work_authorization == null ? "unsure" : p.needs_us_work_authorization ? "yes" : "no",
    edu_degree: e.degree_level || "", edu_field: e.field || "", edu_country: e.country || "", edu_gpa: e.gpa_band || "",
    years_work_experience: p.years_work_experience ?? "", current_industry: p.current_industry || "", current_function: p.current_function || "",
    quantitative_background: p.quantitative_background || "", target_function: p.target_function || "", target_industry: p.target_industry || "",
    target_roles: (p.target_roles || []).join("; "), long_term_location: p.long_term_location || "", preferred_us_states: p.preferred_us_states || [],
    budget_amount: p.budget_usd ?? p.max_total_budget_usd_per_year ?? "", budget_period: p.budget_period === "total_program" ? "total" : "year",
    funding_notes: p.funding_notes || "", test_status: p.test_status || "unknown", test_score: p.test_score ?? "",
    target_intake_year: p.target_intake_year ?? "", weeks_until_first_application: p.weeks_until_first_application ?? "",
    hours_per_week_available: p.hours_per_week_available ?? "", notes: p.notes || "" };
}
function toProfile(d) {
  const edu = d.edu_degree || d.edu_field ? [{ degree_level: d.edu_degree || "Not specified", field: d.edu_field || "Not specified",
    country: d.edu_country || null, gpa_band: d.edu_gpa || null }] : [];
  const amount = num(d.budget_amount);
  return {
    is_fictional: !!d.is_fictional && !!d.pristine, citizenship_country: d.citizenship_country || null,
    needs_us_work_authorization: { yes: true, no: false }[d.needs_us_work_authorization] ?? null, education: edu,
    years_work_experience: num(d.years_work_experience), current_industry: d.current_industry || null, current_function: d.current_function || null,
    target_function: d.target_function || null, target_industry: d.target_industry || null,
    target_roles: (d.target_roles || "").split(/[;\n]/).map(s => s.trim()).filter(Boolean).slice(0, 4),
    preferred_us_states: d.preferred_us_states || [], long_term_location: d.long_term_location || null,
    budget_usd: amount, budget_period: amount == null ? null : (d.budget_period === "total" ? "total_program" : "per_academic_year"),
    funding_notes: d.funding_notes || null, quantitative_background: d.quantitative_background || null,
    test_status: d.test_status || "unknown", test_score: num(d.test_score), target_intake_year: num(d.target_intake_year),
    weeks_until_first_application: num(d.weeks_until_first_application), hours_per_week_available: num(d.hours_per_week_available),
    notes: d.notes ? d.notes.slice(0, 900) : null,
  };
}

/* ---------------- onboarding definition: short, conversational steps ---------------- */
const STATES = [["CT", "Connecticut"], ["MA", "Massachusetts"], ["IL", "Illinois"], ["NC", "North Carolina"], ["TX", "Texas"], ["CA", "California"], ["NY", "New York"]];
const TESTS = [["unknown", "Not sure yet"], ["not_started", "Not started"], ["preparing", "Preparing"], ["gmat_taken", "GMAT taken"],
  ["gmat_focus_taken", "GMAT Focus taken"], ["gre_taken", "GRE taken"], ["ea_taken", "Executive Assessment taken"]];
const SCORE_RANGES = { gmat_taken: [200, 800], gmat_focus_taken: [205, 805], gre_taken: [260, 340], ea_taken: [100, 200] };
const STEPS = [
  { q: "Where are you starting from?", why: "We only ask for your country — never passport or ID numbers. It helps us flag work-authorization questions.",
    fields: [{ k: "citizenship_country", label: "Country of citizenship", ph: "e.g. India" },
      { k: "needs_us_work_authorization", label: "Will you need US work authorization after graduating?", type: "choice",
        options: [["yes", "Yes", "e.g. I'm not a US citizen or permanent resident"], ["no", "No", ""], ["unsure", "Not sure", "We'll treat it as an open question"]] }] },
  { q: "Tell us about your background.", why: "A rough picture is enough. Leave anything blank and it stays unknown — we never guess.",
    fields: [{ pair: [{ k: "edu_degree", label: "Highest degree", type: "select", options: [["", "Select…"], ["Bachelor's", "Bachelor's"], ["Master's", "Master's"], ["Doctorate", "Doctorate"], ["Other", "Other"]] },
      { k: "edu_field", label: "Field of study", ph: "e.g. Computer Engineering" }] },
      { pair: [{ k: "years_work_experience", label: "Years of full-time work", type: "number", min: 0, max: 40, step: 0.5, ph: "e.g. 5" },
        { k: "current_function", label: "Current role", ph: "e.g. Software engineering lead" }] },
      { k: "current_industry", label: "Current industry", ph: "e.g. IT services" }] },
  { q: "Where do you want your career to go?", why: "This is the heart of AdmitCompass: programs are judged by how well they lead here.",
    fields: [{ pair: [{ k: "target_function", label: "Target function", ph: "e.g. Product management", required: true },
      { k: "target_industry", label: "Target industry", ph: "e.g. Technology" }] },
      { k: "target_roles", label: "Roles you're aiming for (optional)", type: "textarea", ph: "e.g. Product Manager at a US tech company; Associate Product Manager", hint: "Separate up to four roles with semicolons." },
      { k: "long_term_location", label: "Where do you want to work long term?", type: "select", options: [["", "Select…"], ["US", "United States"], ["US short term, then home country", "US first, then home country"], ["Home country", "Home country"], ["Flexible", "Flexible"]] }] },
  { q: "Where, and on what budget?", why: "We compare your budget only with each school's published cost of attendance, which is per academic year.",
    fields: [{ k: "preferred_us_states", label: "Preferred locations (optional)", type: "chips" },
      { k: "budget_amount", label: "Your maximum budget (USD)", type: "number", min: 1000, max: 1000000, step: 1000, ph: "e.g. 135000" },
      { k: "budget_period", label: "That budget covers…", type: "choice",
        options: [["year", "One academic year", "Compared directly with each school's published one-year cost of attendance."],
          ["total", "The whole program", "Kept as entered. Because schools publish one-year costs, budget fit will show as unknown rather than guessed."]] },
      { k: "funding_notes", label: "Anything about funding? (optional)", type: "textarea", ph: "e.g. Mostly loans; employer support possible" }] },
  { q: "Tests and timing.", why: "This shapes your GMAT/GRE guidance and how much we put in each week of your plan.",
    fields: [{ pair: [{ k: "test_status", label: "GMAT / GRE status", type: "select", options: TESTS }, { k: "test_score", label: "Score, if taken", type: "number", min: 0, max: 900 }] },
      { pair: [{ k: "target_intake_year", label: "Target start year", type: "select", options: [["", "Select…"], ...[2026, 2027, 2028, 2029, 2030].map(y => [String(y), String(y)])] },
        { k: "weeks_until_first_application", label: "Weeks until first application", type: "number", min: 0, max: 104, ph: "e.g. 10" }] },
      { k: "hours_per_week_available", label: "Hours per week you can invest", type: "number", min: 0, max: 80, ph: "e.g. 12" },
      { k: "notes", label: "Anything else we should know? (optional)", type: "textarea", hint: "Please don't include names, emails, phone or ID numbers." }] },
];
const flatFields = s => s.fields.flatMap(f => f.pair || [f]);

function validateStep(i) {
  const d = S.draft, errs = {};
  const rng = (k, lo, hi) => { const v = num(d[k]); if (d[k] !== "" && d[k] != null && (v == null || v < lo || v > hi)) errs[k] = `Please enter a number from ${lo} to ${hi}.`; };
  if (i === 1) rng("years_work_experience", 0, 40);
  if (i === 2 && !(d.target_function || "").trim() && !(d.target_roles || "").trim()) errs.target_function = "Tell us a target function or at least one role.";
  if (i === 3) rng("budget_amount", 1000, 1000000);
  if (i === 4) {
    rng("weeks_until_first_application", 0, 104); rng("hours_per_week_available", 0, 80);
    const r = SCORE_RANGES[d.test_status];
    if (num(d.test_score) != null) {
      if (!r) errs.test_score = "Choose which test you took, or clear the score.";
      else if (num(d.test_score) < r[0] || num(d.test_score) > r[1]) errs.test_score = `That test is scored from ${r[0]} to ${r[1]}.`;
    }
  }
  return errs;
}

/* ---------------- router ---------------- */
function closeMenu() {
  const b = document.querySelector(".menu-btn"), n = document.getElementById("primary-nav");
  if (!b || !n) return;
  b.setAttribute("aria-expanded", "false"); b.setAttribute("aria-label", "Open menu"); n.classList.remove("open");
}
function setupMenu() {
  const b = document.querySelector(".menu-btn"), n = document.getElementById("primary-nav");
  if (!b || !n) return;
  b.addEventListener("click", () => { const open = b.getAttribute("aria-expanded") !== "true";
    b.setAttribute("aria-expanded", String(open)); b.setAttribute("aria-label", open ? "Close menu" : "Open menu"); n.classList.toggle("open", open);
    if (open) n.querySelector("a")?.focus(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && b.getAttribute("aria-expanded") === "true") { closeMenu(); b.focus(); } });
}
/* Light/dark theme: dark is the default; the choice is remembered in this browser (localStorage "ac-theme"). */
function applyTheme(theme) {
  const dark = theme !== "light";
  const css = document.getElementById("dark-theme"), btn = document.getElementById("theme-toggle");
  if (css) css.disabled = !dark;
  document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#0A0F1E" : "#FFFFFF");
  if (btn) { btn.setAttribute("aria-pressed", dark ? "true" : "false"); btn.title = dark ? "Switch to light theme" : "Switch to dark theme"; }
}
function setupTheme() {
  let saved = null;
  try { saved = localStorage.getItem("ac-theme"); } catch { /* storage blocked: stay dark */ }
  applyTheme(saved === "light" ? "light" : "dark");
  document.getElementById("theme-toggle")?.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
    try { localStorage.setItem("ac-theme", next); } catch { /* not remembered */ }
  });
}
async function boot() {
  setupTheme();
  setupMenu();
  /* Render first; never let a slow or failed background request leave the page empty. */
  window.addEventListener("hashchange", route);
  setupCopilot();
  route();
  const wasUser = !!S.user;
  await api("/api/config").then(c => { S.config = c; }).catch(() => { S.config = null; });
  await loadSession();
  if (!!S.user !== wasUser) route();   // re-render with account-backed saved data once the session is known
}
function setNav(which) { document.querySelectorAll(".nav a").forEach(a => a.classList.toggle("active", a.dataset.nav === which && !a.classList.contains("btn"))); }
const ROUTE_TITLE = {
  home: "AdmitCompass — your career ambition deserves a better education plan",
  explore: "Explore MBA programs · AdmitCompass", how: "How it works · AdmitCompass", intl: "International applicants · AdmitCompass",
  dashboard: "Sample analysis · AdmitCompass", start: "Find your pathway · AdmitCompass",
};
function route() {
  if (S.poll && !location.hash.startsWith("#/run/")) { clearTimeout(S.poll); S.poll = null; }
  let hash = location.hash || "#/", auth = null;
  const am = /^#\/(signin|signup)$/.exec(hash);
  if (am) { auth = am[1]; hash = S.lastHash || "#/"; } else S.lastHash = hash;
  if (auth && document.querySelector("#modal-root .auth")) return;
  if (auth && S.rendered === hash) { openAuth(auth); return; }
  S.rendered = hash;
  if (typeof setChatContext === "function") setChatContext(/^#\/(dashboard|results)\/demo/.test(hash) ? { run: "demo" } : {});
  if (auth) setTimeout(() => openAuth(auth), 0);
  let [, view, arg, sub] = hash.split("/");
  if (view === "profile") view = "start";
  clear($main); window.scrollTo(0, 0);
  closeMenu();
  document.body.classList.remove("on-home");   // renderHome sets it again (solid dark header on the homepage)
  document.title = ROUTE_TITLE[view === "results" || view === "run" ? "dashboard" : view] || ROUTE_TITLE.home;
  if (view === "intl") { setNav("intl"); return renderIntl(); }
  const views = { start: renderStart, explore: renderExplore, how: renderHow };
  if (views[view]) { setNav(view); return views[view](); }
  if (view === "run" && arg) { setNav(""); return renderRun(arg); }
  if (view === "dashboard" && arg) { setNav(arg === "demo" ? "results" : ""); return renderDashboard(arg); }
  if (view === "results") { setNav(arg === "demo" ? "results" : ""); return renderResults(arg, sub); }
  setNav("home"); renderHome();
}

/* ---------------- landing ---------------- */
async function loadFixture(key) {
  const fx = await api("/api/fixtures");
  S.draft = draftFromProfile(fx[key].profile, key); S.step = STEPS.length; saveDraft();
  toast(`Loaded a fictional ${key === "tech-pm" ? "tech product manager" : "energy finance"} applicant.`);
  location.hash = "#/start";
}
/* Small inline icons (static path data only). */
const ICONS = {
  check: "M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z",
  checkCircle: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm-1.5 14.5-4-4 1.4-1.4 2.6 2.6 5.6-5.6 1.4 1.4-7 7z",
  alert: "M12 2 1 21h22L12 2zm1 15h-2v-2h2v2zm0-4h-2V9h2v4z",
  search: "M10 2a8 8 0 0 1 6.3 12.9l5.4 5.4-1.4 1.4-5.4-5.4A8 8 0 1 1 10 2zm0 2a6 6 0 1 0 0 12 6 6 0 0 0 0-12z",
  heart: "M12 21s-7.5-4.6-9.5-9.2C1 8.5 3.2 5 6.6 5c2 0 3.4 1.1 4.4 2.5C12 6.1 13.4 5 15.4 5 18.8 5 21 8.5 19.5 11.8 17.5 16.4 12 21 12 21z",
  plus: "M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5z",
  target: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12zm0 3a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  route: "M6 3a3 3 0 0 1 1 5.8V12a2 2 0 0 0 2 2h6a4 4 0 0 1 4 4v.2A3 3 0 1 1 17 18v-.1A2 2 0 0 0 15 16H9a4 4 0 0 1-4-4V8.8A3 3 0 0 1 6 3z",
  shield: "M12 2 4 5v6c0 5 3.4 9.3 8 11 4.6-1.7 8-6 8-11V5l-8-3zm-1 13-3.5-3.5 1.4-1.4L11 12.2l4.1-4.1 1.4 1.4L11 15z",
  list: "M4 5h2v2H4V5zm4 0h12v2H8V5zm-4 6h2v2H4v-2zm4 0h12v2H8v-2zm-4 6h2v2H4v-2zm4 0h12v2H8v-2z",
  globe: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm6.9 6h-3a15 15 0 0 0-1.3-4A8 8 0 0 1 18.9 8zM12 4c.8 1.1 1.5 2.5 1.9 4h-3.8c.4-1.5 1.1-2.9 1.9-4zM4.3 14a8 8 0 0 1 0-4h3.4a16 16 0 0 0 0 4H4.3zm.8 2h3a15 15 0 0 0 1.3 4A8 8 0 0 1 5.1 16zm3-8h-3a8 8 0 0 1 4.3-4 15 15 0 0 0-1.3 4zM12 20c-.8-1.1-1.5-2.5-1.9-4h3.8c-.4 1.5-1.1 2.9-1.9 4zm2.3-6H9.7a14 14 0 0 1 0-4h4.6a14 14 0 0 1 0 4zm.3 6a15 15 0 0 0 1.3-4h3a8 8 0 0 1-4.3 4zm1.7-6a16 16 0 0 0 0-4h3.4a8 8 0 0 1 0 4h-3.4z",
  dollar: "M11 2h2v2.1c2.3.4 4 2 4 4.2h-2c0-1.2-1.3-2.3-3-2.3s-3 1-3 2.2c0 1.3 1.2 1.9 3.3 2.4 2.6.6 4.7 1.6 4.7 4.2 0 2.2-1.7 3.8-4 4.2V21h-2v-2c-2.4-.4-4.2-2.1-4.2-4.4h2c0 1.3 1.5 2.5 3.2 2.5 1.8 0 3-1 3-2.3 0-1.4-1.3-1.9-3.5-2.4C8.8 11.8 7 10.8 7 8.4c0-2.1 1.7-3.8 4-4.2V2z",
  chart: "M4 20V10h3v10H4zm6.5 0V4h3v16h-3zM17 20v-7h3v7h-3z",
  user: "M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm0 2c-4.4 0-8 2.2-8 5v2h16v-2c0-2.8-3.6-5-8-5z",
  book: "M5 4a2 2 0 0 1 2-2h12v16H7a2 2 0 0 0-2 2V4zm2 16h12v2H7a2 2 0 0 1 0-4z",
  briefcase: "M9 3h6a2 2 0 0 1 2 2v1h3a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h3V5a2 2 0 0 1 2-2zm0 3h6V5H9v1z",
  sliders: "M3 6h10v2H3V6zm14 0h4v2h-4V6zm-2-2h2v6h-2V4zM3 16h4v2H3v-2zm8 0h10v2H11v-2zm-2-2h2v6H9v-6z",
};
function svgIcon(name) {
  const s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("aria-hidden", "true"); s.setAttribute("focusable", "false");
  const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
  p.setAttribute("d", ICONS[name]); p.setAttribute("fill", "currentColor"); s.appendChild(p);
  return s;
}
const arrow = () => el("span", { class: "arrow", "aria-hidden": "true", text: "→" });
const kUSD = v => (v == null ? "—" : `$${Math.round(v / 1000)}k`);

/* Interactive product preview: the real saved analysis only (/api/dashboard/demo = saved run + deterministic checks). */

/* Product roadmap: what is live now, and three later stages. Text only — no buttons, data or workflows for
   features that don't exist yet; every later stage carries one "Coming next" label. */
const ROADMAP = [
  ["Apply", "Essays, a story bank and admissions interview practice, built on the career story and evidence you already have.",
    ["Application essays", "Story bank", "Admissions interviews"]],
  ["Prepare", "Visa guidance pointers and a structured way to plan networking and coffee chats before you arrive.",
    ["Visa preparation", "Networking", "Coffee chats"]],
  ["Recruit", "Employer sponsorship research, recruiting timelines, case practice and events for your target role.",
    ["Sponsorship research", "Recruiting", "Case practice", "Events and community"]],
];
function roadmap() {
  return el("section", { class: "rm", "aria-labelledby": "rm-h" },
    el("h2", { id: "rm-h", class: "rm-h", text: "Your full journey, built in stages" }),
    el("p", { class: "rm-lead", text: "This release covers the first stage: matching programs to your career goal, choosing between the GRE and GMAT, finding profile gaps and turning them into weekly actions." }),
    el("ol", { class: "rm-path" },
      el("li", { class: "rm-stage now" }, el("span", { class: "rm-node", "aria-hidden": "true" }),
        el("div", {}, el("div", { class: "rm-top" }, el("h3", { text: "Match and plan" }), el("span", { class: "rm-tag now", text: "Available now" })),
          el("p", { text: "School shortlist, GRE-or-GMAT decision, profile gaps and a weekly plan — with every fact traced to an official source." }))),
      ROADMAP.map(([name, value, items]) => el("li", { class: "rm-stage" }, el("span", { class: "rm-node", "aria-hidden": "true" }),
        el("div", {}, el("div", { class: "rm-top" }, el("h3", { text: name }), el("span", { class: "rm-tag", text: "Coming next" })),
          el("p", { text: value }),
          el("p", { class: "rm-items", text: items.join(" · ") }))))));
}
async function renderHome(scrollTo) {
  document.body.classList.add("on-home");
  const grid = el("div", { class: "show-grid" }, el("p", { class: "small muted", text: "Loading programs…" }));
  put($main,
    el("section", { class: "hp2-hero" },
      el("div", { class: "wrap hp2-grid" },
        el("div", { class: "hp2-copy" },
          el("span", { class: "hp2-eyebrow", text: "Career-first MBA guidance" }),
          el("h1", {}, "Your career ambition deserves ", el("span", { class: "grad", text: "a better education plan." })),
          el("p", { class: "hp2-sub", text: "Match MBA programs to the career you want, settle the GRE-or-GMAT question, and turn your gaps into a weekly plan — with every claim traced to its official source." }),
          el("div", { class: "hp2-cta" },
            el("a", { class: "btn btn-primary btn-lg", href: "#/start" }, "Find my pathway ", arrow()),
            el("a", { class: "btn btn-ghost-light btn-lg", href: "#/explore", text: "Explore programs" })),
          el("p", { class: "hp2-sample" }, el("a", { href: "#/dashboard/demo" }, "Or open a sample dashboard (fictional applicant) ", arrow()))),
        el("div", { class: "hp2-flow", "aria-labelledby": "hp2-flow-h" },
          el("h2", { id: "hp2-flow-h", class: "hp2-flow-k", text: "How AdmitCompass helps" }),
          el("ol", {}, [
            ["Match programs to your career goal", "Shortlisted by where they lead, not by prestige."],
            ["Decide between the GRE and GMAT", "Using each program's official test policy."],
            ["Turn profile gaps into weekly actions", "A week-by-week plan sized to your time."]]
            .map(([h, t], n) => el("li", {}, el("span", { class: "num", "aria-hidden": "true", text: String(n + 1) }), el("div", {}, el("b", { text: h }), el("span", { text: t })))))))),
    el("section", { class: "hp2-sec hp2-proofsec", id: "how" }, el("div", { class: "wrap" },
      el("ul", { class: "hp2-points" }, [
        ["shield", "Evidence linked to official sources."],
        ["route", "Recommendations explain tradeoffs and unknowns."],
        ["list", "Plans turn decisions into next actions."]].map(([i, t]) => el("li", {}, el("span", { class: "ic" }, svgIcon(i)), t))),
      roadmap())),
    el("section", { class: "hp2-sec tint", id: "programs" }, el("div", { class: "wrap" },
      el("div", { class: "sec2-head row2" }, el("div", {}, el("span", { class: "eyebrow2 violet", text: "Real, sourced information" }), el("h2", { text: "Leading MBA programs, with the evidence shown" }),
        el("p", { text: "Each card says what's sourced from official pages and what isn't. Unknown stays unknown." })),
        el("a", { class: "btn btn-outline", href: "#/explore" }, "Explore all programs ", arrow())),
      grid)),
    el("section", { class: "hp2-sec", id: "intl" }, el("div", { class: "wrap intl3" },
      el("div", { class: "sec2-head" }, el("span", { class: "eyebrow2 cyan", text: "For international applicants" }), el("h2", { text: "Straight answers where generic advice gets it wrong" }),
        el("p", { text: "Work authorization, total cost and real outcomes matter most when you apply from abroad. AdmitCompass shows the evidence — and says clearly when there isn't any." }),
        el("div", { class: "hp2-cta" }, el("a", { class: "btn btn-primary", href: "#/intl" }, "Read the international guide ", arrow()),
          el("a", { class: "btn btn-outline", href: "#/dashboard/demo", text: "See a sample analysis" }))),
      el("div", { class: "intl3-grid" }, [
        ["shield", "STEM status, with its source", "Shown only when an official university page says so — never presented as a visa guarantee."],
        ["globe", "Sponsorship is never assumed", "Without employer-specific evidence, sponsorship stays unknown."],
        ["dollar", "Total cost, not just tuition", "Your budget is compared only with a published one-year cost of attendance."],
        ["chart", "Outcomes with definitions", "Employment figures keep their cohorts and definitions, and aren't ranked when they differ."]]
        .map(([i, h, t]) => el("div", { class: "intl3-card" }, el("span", { class: "ic" }, svgIcon(i)), el("h3", { text: h }), el("p", { text: t })))))),
    el("section", { class: "hp2-sec", style: "padding-top:0" }, el("div", { class: "wrap" }, el("div", { class: "hp2-final" },
      el("div", {}, el("h2", { text: "Find the program that fits where you're going." }), el("p", { text: "About five minutes of questions. No admission odds, no guarantees — just evidence and a plan." })),
      el("div", { class: "hp2-cta" }, el("a", { class: "btn btn-light btn-lg", href: "#/start" }, "Find my pathway ", arrow()),
        el("a", { class: "btn btn-ghost-light btn-lg", href: "#/dashboard/demo", text: "View sample analysis" }))))));
  if (scrollTo) document.getElementById(scrollTo)?.scrollIntoView({ block: "start" });
  try {
    const r = await api("/api/programs");
    const items = r.items.filter(it => it.tier === "verified").slice(0, 3);
    put(clear(grid), items.map((it, i) => {
      const coa = it.cost_of_attendance, stem = it.stem_designated === true ? (it.stem_partial ? "Some tracks" : "Verified") : "Unknown";
      return el("article", { class: "show-card" },
        el("div", { class: "show-top" }, el("span", { class: "logo", style: `background:${LOGO_COLORS[i % LOGO_COLORS.length]}`, "aria-hidden": "true", text: initials(it.school || it.university) }),
          el("div", {}, el("h3", { text: shortName(it) }), el("div", { class: "xs muted", text: [it.city, it.state].filter(Boolean).join(", ") }))),
        el("span", { class: `ev2 ${it.evidence_status}`, text: it.evidence_label }),
        el("dl", {},
          coa ? el("div", {}, el("dt", { text: "Cost of attendance" }), el("dd", { text: `${fmtUSD(coa.value)} / yr (${coa.period})` }))
            : it.costs?.estimate_annual ? el("div", {}, el("dt", { text: "Estimated cost" }), el("dd", { text: `${fmtUSD(it.costs.estimate_annual.value)} / yr (${it.costs.estimate_annual.publisher} estimate)` }))
            : el("div", {}, el("dt", { text: "Cost of attendance" }), el("dd", { class: "unk", text: "Not on official pages checked" })),
          el("div", {}, el("dt", { text: "STEM designation" }), el("dd", { class: stem === "Verified" ? "" : "unk", text: stem })),
          el("div", {}, el("dt", { text: "Employment rate" }), el("dd", { class: it.employment ? "" : "unk", text: it.employment ? `${it.employment.rate}% (${it.employment.period})` : "Not on official pages checked" }))),
        it.official_link?.url ? extLink(it.official_link.final_url || it.official_link.url, "Official page") : null);
    }));
  } catch { put(clear(grid), el("p", { class: "small muted", text: "Programs could not be loaded." })); }
  if (scrollTo && location.hash === "#/" + scrollTo) document.getElementById(scrollTo)?.scrollIntoView({ block: "start" });
}

/* ---------------- accounts: sign in / sign up / sign out ----------------
   The session lives in an HttpOnly cookie set by the server; JS never sees or stores it. The CSRF token from
   /api/auth/me is kept in memory only and sent as X-CSRF-Token on writes. */
async function loadSession() {
  if (!S.config?.accounts_enabled) { S.user = null; S.csrf = null; S.accountSaved = []; renderNavAuth(); return; }   // accounts off (default)
  try { const r = await api("/api/auth/me"); S.user = r.user; S.csrf = r.csrf_token || null; } catch { S.user = null; S.csrf = null; }
  S.accountSaved = [];
  if (S.user) { try { S.accountSaved = (await api("/api/account/saved")).program_ids; } catch { /* keep empty */ } }
  renderNavAuth();
}
function renderNavAuth() {
  const box = document.querySelector(".nav-auth");
  if (!box) return;
  clear(box);
  box.hidden = !S.config?.accounts_enabled;
  if (box.hidden) return;
  if (S.user) {
    put(box, el("span", { class: "acct", title: S.user.email }, el("span", { class: "acct-av", "aria-hidden": "true", text: (S.user.name || "?").trim()[0].toUpperCase() }),
      el("span", { class: "acct-name", text: S.user.name })),
      el("button", { type: "button", class: "btn btn-outline", id: "signout-btn", onclick: signOut, text: "Sign Out" }));
  } else {
    put(box, el("a", { href: "#/signin", class: "btn btn-outline", "data-nav": "signin", text: "Sign In" }),
      el("a", { href: "#/signup", class: "btn btn-primary", "data-nav": "signup", text: "Sign Up" }));
  }
}
async function signOut() {
  const b = document.getElementById("signout-btn"); if (b) { b.disabled = true; b.textContent = "Signing out…"; }
  try { await api("/api/auth/logout", { method: "POST" }); }
  catch (err) { toast(`Sign-out failed: ${err.message}`); if (b) { b.disabled = false; b.textContent = "Sign Out"; } return; }
  S.user = null; S.csrf = null; S.accountSaved = [];
  renderNavAuth(); closeMenu();
  toast("You're signed out.");
  if (location.hash === "#/" || location.hash === "") route(); else location.hash = "#/";
}
function localData() {
  const saved = JSON.parse(localStorage.getItem("ac-saved") || "[]");
  const progress = {};
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i), m = /^ac-workspace-(.+)$/.exec(k || "");
    if (!m) continue;
    try { const ids = Object.entries(JSON.parse(localStorage.getItem(k)) || {}).filter(([, v]) => v === true).map(([id]) => id); if (ids.length) progress[m[1]] = ids; } catch { /* skip */ }
  }
  return { saved: Array.isArray(saved) ? saved : [], progress };
}
function modal(labelId, build, onClose) {
  const root = document.getElementById("modal-root"), opener = document.activeElement;
  const teardown = () => { clear(root); document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  const close = () => { teardown(); onClose?.(); opener?.focus?.(); };
  const onKey = e => {
    if (e.key === "Escape") { e.preventDefault(); close(); return; }
    if (e.key !== "Tab") return;
    const f = [...root.querySelectorAll("button:not([disabled]), a[href], input:not([disabled])")]; if (!f.length) return;
    if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
  };
  const dlg = el("div", { class: "modal auth", role: "dialog", "aria-modal": "true", "aria-labelledby": labelId });
  const bg = el("div", { class: "modal-bg auth-bg", onmousedown: e => { if (e.target === bg) close(); } }, dlg);
  put(clear(root), bg);
  document.addEventListener("keydown", onKey);
  document.body.style.overflow = "hidden";
  build(dlg, { close, teardown });
}
async function offerImport() {
  const ld = localData();
  /* only offer what isn't already in the account */
  const have = new Set(S.accountSaved || []);
  ld.saved = ld.saved.filter(x => !have.has(x));
  for (const run of Object.keys(ld.progress)) {
    try { const done = new Set((await api(`/api/account/progress/${encodeURIComponent(run)}`)).done); ld.progress[run] = ld.progress[run].filter(t => !done.has(t)); }
    catch { /* keep: the server validates and skips duplicates */ }
    if (!ld.progress[run].length) delete ld.progress[run];
  }
  const nTasks = Object.values(ld.progress).reduce((a, x) => a + x.length, 0);
  if (!ld.saved.length && !nTasks) return;
  modal("imp-h", (dlg, { close }) => {
    const status = el("p", { class: "small", role: "status", "aria-live": "polite" });
    const go = el("button", { type: "button", class: "btn btn-primary", onclick: async () => {
      go.disabled = true; go.textContent = "Importing…";
      try {
        const r = await api("/api/account/import", { method: "POST", body: JSON.stringify(ld) });
        S.accountSaved = (await api("/api/account/saved")).program_ids;
        close(); toast(`Imported ${r.saved_added} saved program${r.saved_added === 1 ? "" : "s"} and ${r.tasks_added} completed task${r.tasks_added === 1 ? "" : "s"}` +
          (r.saved_duplicates + r.tasks_duplicates ? ` (${r.saved_duplicates + r.tasks_duplicates} already in your account)` : "") + ".");
        route();
      } catch (err) { status.textContent = `Import failed: ${err.message}`; go.disabled = false; go.textContent = "Import into my account"; }
    } }, "Import into my account");
    put(dlg, el("div", { class: "auth-head" }, el("span", { class: "pvtag", text: "Optional" }),
      el("button", { class: "close-btn", type: "button", "aria-label": "Close", onclick: close, text: "×" })),
      el("h2", { id: "imp-h", text: "Add this browser's saved work to your account?" }),
      el("p", { text: "You saved some work in this browser before signing in. Importing only adds items to your account — nothing in your account is replaced or deleted, and duplicates are skipped." }),
      el("ul", { class: "auth-list" },
        ld.saved.length ? el("li", {}, svgIcon("check"), el("span", { text: `${ld.saved.length} saved program${ld.saved.length === 1 ? "" : "s"}` })) : null,
        nTasks ? el("li", {}, svgIcon("check"), el("span", { text: `${nTasks} completed roadmap task${nTasks === 1 ? "" : "s"}` })) : null),
      el("div", { class: "auth-actions" }, go, el("button", { type: "button", class: "btn btn-outline", onclick: close, text: "Not now" })),
      status, el("p", { class: "xs muted", text: "Your browser copy stays as it is, so it remains available when you're signed out." }));
    go.focus();
  });
}
function openAuth(mode) {
  if (!S.config?.accounts_enabled) { history.replaceState(null, "", S.lastHash || "#/"); return; }
  if (S.user) { history.replaceState(null, "", S.lastHash || "#/"); return; }
  const back = S.lastHash || "#/", signup = mode === "signup";
  modal("auth-h", (dlg, { close, teardown }) => {
    const errs = {};
    const field = (name, label, type, auto, extra = {}) => {
      const id = `af-${name}`, err = el("div", { class: "ferr", id: `${id}-err`, role: "alert" });
      const input = el("input", { id, name, type, autocomplete: auto, required: true, "aria-describedby": `${id}-err`, ...extra });
      errs[name] = { input, err };
      const wrap = el("div", { class: "fld" }, el("label", { for: id, text: label }));
      if (type === "password") {
        const tog = el("button", { type: "button", class: "pw-toggle", "aria-label": `Show ${label.toLowerCase()}`, "aria-pressed": "false", text: "Show",
          onclick: () => { const show = input.type === "password"; input.type = show ? "text" : "password"; tog.textContent = show ? "Hide" : "Show";
            tog.setAttribute("aria-pressed", String(show)); tog.setAttribute("aria-label", `${show ? "Hide" : "Show"} ${label.toLowerCase()}`); } });
        put(wrap, el("div", { class: "pw-wrap" }, input, tog));
      } else put(wrap, input);
      return put(wrap, err);
    };
    const formErr = el("div", { class: "form-err", role: "alert" });
    const submit = el("button", { type: "submit", class: "btn btn-primary" }, signup ? "Create account" : "Sign in");
    const form = el("form", { novalidate: true, class: "auth-form" },
      signup ? field("name", "Name", "text", "name", { maxlength: "80" }) : null,
      field("email", "Email", "email", "email", { maxlength: "254", inputmode: "email" }),
      field("password", "Password", "password", signup ? "new-password" : "current-password", { maxlength: "128" }),
      signup ? el("p", { class: "xs muted hint", text: "At least 10 characters." }) : null,
      signup ? field("password_confirm", "Confirm password", "password", "new-password", { maxlength: "128" }) : null,
      formErr, submit);
    const setErrors = (fields = {}, msg = "") => {
      for (const [k, { input, err }] of Object.entries(errs)) { err.textContent = fields[k] || ""; input.setAttribute("aria-invalid", fields[k] ? "true" : "false"); }
      formErr.textContent = msg;
      const first = Object.keys(fields).find(k => errs[k]); if (first) errs[first].input.focus();
    };
    form.addEventListener("submit", async e => {
      e.preventDefault();
      const v = Object.fromEntries(Object.entries(errs).map(([k, x]) => [k, x.input.value]));
      const local = {};
      if (signup && !v.name.trim()) local.name = "Enter your name.";
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(v.email.trim())) local.email = "Enter a valid email address.";
      if (!v.password) local.password = "Enter your password.";
      else if (signup && v.password.length < 10) local.password = "Use at least 10 characters.";
      if (signup && v.password !== v.password_confirm) local.password_confirm = "Passwords don't match.";
      if (Object.keys(local).length) { setErrors(local, "Please fix the highlighted fields."); return; }
      setErrors();
      submit.disabled = true; submit.setAttribute("aria-busy", "true"); submit.textContent = signup ? "Creating account…" : "Signing in…";
      try {
        const r = await api(signup ? "/api/auth/signup" : "/api/auth/login", { method: "POST", body: JSON.stringify(v) });
        S.user = r.user; S.csrf = r.csrf_token;   // only after the server confirmed
        await loadSession();
        teardown(); history.replaceState(null, "", back);
        toast(signup ? `Welcome, ${S.user.name}! Your account is ready.` : `Signed in as ${S.user.name}.`);
        route();
        offerImport();
      } catch (err) {
        setErrors(err.fields || {}, err.message);
        submit.disabled = false; submit.removeAttribute("aria-busy"); submit.textContent = signup ? "Create account" : "Sign in";
      }
    });
    put(dlg, el("div", { class: "auth-head" }, el("span", { class: "brand-mini", text: "AdmitCompass" }),
      el("button", { class: "close-btn", type: "button", "aria-label": "Close", onclick: close, text: "×" })),
      el("h2", { id: "auth-h", text: signup ? "Create your account" : "Welcome back" }),
      el("p", { text: signup ? "Save programs, your profile and roadmap progress to your account. Everything else works without one." : "Sign in to see your saved programs, profile and progress." }),
      form,
      el("p", { class: "xs muted auth-switch" }, signup ? "Already have an account? " : "New to AdmitCompass? ",
        el("button", { type: "button", class: "linkbtn", onclick: () => { teardown(); history.replaceState(null, "", `#/${signup ? "signin" : "signup"}`); openAuth(signup ? "signin" : "signup"); }, text: signup ? "Sign in" : "Create an account" })),
      el("p", { class: "xs muted auth-switch" }, el("button", { type: "button", class: "linkbtn", onclick: () => { teardown(); location.hash = "#/start"; }, text: "Continue without an account" })),
      signup ? null : el("p", { class: "xs muted auth-switch", text: "Forgot your password? Password reset isn't available yet (no email service is configured)." }));
    (errs.name || errs.email).input.focus();
  }, () => history.replaceState(null, "", back));
}

/* ---------------- onboarding ---------------- */
function renderStart() {
  const total = STEPS.length + 1, i = Math.min(S.step, STEPS.length);
  const wrap = el("div", { class: "wrap narrow onb" });
  put(wrap, 
    el("div", { class: "spread xs muted" }, el("span", { text: i < STEPS.length ? `Step ${i + 1} of ${STEPS.length}` : "Review" }),
      el("span", { class: "row" }, S.user ? el("button", { class: "link-btn xs", onclick: async () => {
        try { const r = await api("/api/account/profile"); if (!r.profile) { toast("No profile saved in your account yet."); return; }
          S.draft = draftFromProfile(r.profile, null); saveDraft(); S.step = STEPS.length; rerenderStart(); toast("Loaded your saved profile."); }
        catch (err) { toast(err.message); } }, text: "Load my saved profile" }) : null,
      S.draft.source ? el("span", { text: `Fictional sample applicant${S.draft.pristine ? "" : " (edited)"}` }) : el("button", { class: "link-btn xs", onclick: () => loadFixture("tech-pm"), text: "Use a sample applicant" }))),
    el("div", { class: "progress", role: "progressbar", "aria-valuemin": 1, "aria-valuemax": total, "aria-valuenow": i + 1, "aria-label": "Progress" },
      el("div", { style: `width:${((i + 1) / total) * 100}%` })));
  const body = el("div");
  put(wrap, body);
  put($main, wrap);
  i < STEPS.length ? renderStep(body, i) : renderReview(body);
}
function rerenderStart() { clear($main); renderStart(); window.scrollTo(0, 0); }
function control(f, errs) {
  const d = S.draft, id = `f-${f.k}`, invalid = errs[f.k] ? "true" : null;
  const set = v => { d[f.k] = v; d.pristine = false; saveDraft(); };
  let ctl;
  if (f.type === "select") {
    ctl = el("select", { id, "aria-invalid": invalid, onchange: e => set(e.target.value) },
      f.options.map(([v, t]) => el("option", { value: v, text: t, selected: String(d[f.k] ?? "") === v ? true : null })));
  } else if (f.type === "textarea") {
    ctl = el("textarea", { id, "aria-invalid": invalid, maxlength: 900, placeholder: f.ph || null, oninput: e => set(e.target.value) }); ctl.value = d[f.k] || "";
  } else if (f.type === "chips") {
    ctl = el("div", { class: "chips", role: "group", "aria-labelledby": `${id}-l` }, STATES.map(([code, name]) => {
      const on = (d.preferred_us_states || []).includes(code);
      return el("button", { type: "button", class: "chip", "aria-pressed": on ? "true" : "false", text: name, onclick: e => {
        const s = new Set(d.preferred_us_states || []); s.has(code) ? s.delete(code) : s.add(code); set([...s]);
        e.currentTarget.setAttribute("aria-pressed", s.has(code) ? "true" : "false"); } });
    }));
  } else if (f.type === "choice") {
    const cur = d[f.k] ?? (f.k === "budget_period" ? "year" : "unsure");
    ctl = el("div", { class: "choices", role: "radiogroup", "aria-labelledby": `${id}-l` }, f.options.map(([v, t, sub]) =>
      el("button", { type: "button", class: "choice", role: "radio", "aria-pressed": cur === v ? "true" : "false", "aria-checked": cur === v ? "true" : "false",
        onclick: e => { set(v); e.currentTarget.parentNode.querySelectorAll(".choice").forEach(b => { const on = b === e.currentTarget; b.setAttribute("aria-pressed", on); b.setAttribute("aria-checked", on); }); } },
        el("span", { class: "dot", "aria-hidden": "true" }), el("span", {}, el("b", { text: t }), sub ? el("span", { class: "sub", text: sub }) : null))));
  } else {
    ctl = el("input", { id, type: f.type || "text", min: f.min, max: f.max, step: f.step, placeholder: f.ph || null, "aria-invalid": invalid,
      inputmode: f.type === "number" ? "decimal" : null, maxlength: f.type ? null : 120, oninput: e => set(e.target.value) });
    ctl.value = d[f.k] ?? "";
  }
  const isGroup = ["chips", "choice"].includes(f.type);
  return el("div", { class: "field" },
    isGroup ? el("div", { class: "lbl", id: `${id}-l`, text: f.label + (f.required ? " *" : ""), style: "font-weight:600;font-size:15px;margin-bottom:8px" })
      : el("label", { class: "lbl", for: id, text: f.label + (f.required ? " *" : "") }),
    ctl, f.hint ? el("div", { class: "hint", text: f.hint }) : null,
    errs[f.k] ? el("div", { class: "err", role: "alert", text: errs[f.k] }) : null);
}
function renderStep(body, i, errs = {}) {
  clear(body);
  const s = STEPS[i];
  put(body, el("h1", { class: "q", text: s.q }), el("p", { class: "why", text: s.why }),
    s.fields.map(f => f.pair ? el("div", { class: "pair" }, f.pair.map(p => control(p, errs))) : control(f, errs)),
    el("div", { class: "actions" },
      i > 0 ? el("button", { class: "btn btn-quiet", onclick: () => { S.step = i - 1; rerenderStart(); }, text: "Back" }) : el("span"),
      el("button", { class: "btn btn-primary", onclick: () => {
        const e = validateStep(i);
        if (Object.keys(e).length) { renderStep(body, i, e); body.querySelector("[aria-invalid=true]")?.focus(); return; }
        S.step = i + 1; rerenderStart();
      }, text: i === STEPS.length - 1 ? "Review my answers" : "Continue" })));
  body.querySelector("input, select, textarea, .choice, .chip")?.focus({ preventScroll: true });
}
function renderReview(body) {
  const p = toProfile(S.draft), d = S.draft;
  const firstBad = STEPS.findIndex((_, j) => Object.keys(validateStep(j)).length);
  const show = v => (v == null || v === "" || (Array.isArray(v) && !v.length) ? el("span", { class: "muted", text: "Not provided — stays unknown" }) : String(Array.isArray(v) ? v.join(", ") : v));
  const sec = (title, j, rows) => el("section", {},
    el("div", { class: "spread" }, el("h3", { text: title }), el("button", { class: "link-btn", onclick: () => { S.step = j; rerenderStart(); }, text: "Edit" })),
    el("dl", {}, rows.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", {}, show(v))])));
  const budget = p.budget_usd == null ? null : p.budget_period === "total_program"
    ? `${fmtUSD(p.budget_usd)} for the whole program (budget fit will show as unknown)` : `${fmtUSD(p.budget_usd)} per academic year`;
  put(body, el("h1", { class: "q", text: "Does this look right?" }),
    el("p", { class: "why", text: "Edit anything before we start. Blank answers are passed on as unknown." }),
    el("div", { class: "review" },
      sec("Starting point", 0, [["Citizenship", p.citizenship_country], ["Needs US work authorization", { true: "Yes", false: "No" }[p.needs_us_work_authorization] || "Not sure"]]),
      sec("Background", 1, [["Education", p.education.map(e => `${e.degree_level} in ${e.field}`)], ["Experience", p.years_work_experience != null ? `${p.years_work_experience} years` : null],
        ["Current role", [p.current_function, p.current_industry].filter(Boolean)]]),
      sec("Career goal", 2, [["Target", [p.target_function, p.target_industry].filter(Boolean).join(" in ")], ["Roles", p.target_roles], ["Long term", p.long_term_location]]),
      sec("Location and budget", 3, [["Preferred states", p.preferred_us_states], ["Budget", budget], ["Funding", p.funding_notes]]),
      sec("Tests and timing", 4, [["Test", (TESTS.find(t => t[0] === p.test_status) || [, p.test_status])[1]], ["Score", p.test_score],
        ["Start year", p.target_intake_year], ["Weeks to first application", p.weeks_until_first_application], ["Hours per week", p.hours_per_week_available]])),
    firstBad >= 0 ? note("bad", "One answer needs attention.", el("button", { class: "link-btn", onclick: () => { S.step = firstBad; rerenderStart(); }, text: "Fix it" })) : null,
    el("div", { class: "actions" },
      el("button", { class: "btn btn-quiet", onclick: () => { S.step = STEPS.length - 1; rerenderStart(); }, text: "Back" }),
      el("div", { class: "row" },
        d.source === "tech-pm" && d.pristine ? el("a", { class: "btn btn-quiet", href: "#/results/demo", text: "View saved analysis" }) : null,
        S.user ? el("button", { class: "btn btn-quiet", type: "button", onclick: async e => { const b = e.currentTarget; b.disabled = true; b.textContent = "Saving…";
          try { const { profile_id, is_fictional, ...rest } = toProfile(S.draft); await api("/api/account/profile", { method: "PUT", body: JSON.stringify(rest) }); b.textContent = "Saved to account ✓"; }
          catch (err) { b.disabled = false; b.textContent = "Save profile to account"; toast(`Not saved: ${err.message}`); } }, text: "Save profile to account" }) : null,
        runButton(firstBad < 0))),
    runBlockReason() ? el("p", { class: "xs muted", style: "margin-top:12px;text-align:right", text: runBlockReason() }) : null);
}
function runBlockReason() {
  const c = S.config;
  if (!c) return "The server configuration could not be loaded.";
  if (!c.api_key_configured) return "Live analysis needs a PORTKEY_API_KEY on the server. You can still view the sample analysis.";
  if (c.live_run_active) return "An analysis is already running.";
  if (c.live_runs_used >= c.live_runs_allowed) return `This server session has used its ${c.live_runs_allowed} live analyses. Restart the server to reset.`;
  return null;
}
function runButton(valid) {
  return el("button", { class: "btn btn-primary", disabled: !valid || runBlockReason() ? true : null, onclick: confirmRun, text: "Run my analysis" });
}
function confirmRun() {
  const c = S.config, root = document.getElementById("modal-root");
  const opener = document.activeElement;
  const close = () => { clear(root); document.removeEventListener("keydown", onKey); if (opener && opener.focus) opener.focus(); };
  const onKey = e => { if (e.key === "Escape" && !busy) close(); };
  let busy = false;
  const go = el("button", { class: "btn btn-teal", text: "Start analysis", onclick: async e => {
    if (busy) return; busy = true; e.currentTarget.disabled = true; e.currentTarget.textContent = "Starting…";
    try {
      const r = await api("/api/runs", { method: "POST", body: JSON.stringify({ profile: toProfile(S.draft), confirm_paid_run: true }) });
      close(); S.config = await api("/api/config").catch(() => S.config); location.hash = `#/run/${r.run_id}`;
    } catch (err) { close(); toast(err.message); S.config = await api("/api/config").catch(() => S.config); rerenderStart(); }
  } });
  document.addEventListener("keydown", onKey);
  put(root, el("div", { class: "modal-bg", role: "dialog", "aria-modal": "true", "aria-labelledby": "m-title", onclick: e => { if (e.target === e.currentTarget && !busy) close(); } },
    el("div", { class: "modal" },
      el("h2", { id: "m-title", text: "Start a live analysis?" }),
      el("p", { class: "muted", text: `This uses ${c.model} through the course API and costs real money. A typical run takes about a minute.` }),
      el("ul", { class: "small", style: "padding-left:18px" },
        el("li", { text: `Hard limits: ${c.max_requests} model requests, ${fmtInt(c.max_total_tokens)} tokens, ${Math.round(c.max_seconds)} seconds.` }),
        el("li", { text: "Cost per run is unknown — no published gpt-6-luna price." }),
        el("li", { text: `Live analyses left this session: ${c.live_runs_allowed - c.live_runs_used}.` }),
        el("li", { text: "Your answers stay in server memory for this session only." })),
      el("div", { class: "row", style: "justify-content:flex-end;margin-top:24px" }, el("button", { class: "btn btn-quiet", onclick: close, text: "Cancel" }), go))));
  go.focus();
}

/* ---------------- explore programs ---------------- */
const LOGO_COLORS = ["#1D4ED8", "#6D28D9", "#0E7490", "#047857", "#4338CA", "#BE185D", "#334155", "#7E22CE"];
const initials = s => s.replace(/^(The|University of)\s+/i, "").split(/[\s,&-]+/).filter(w => w && w[0] === w[0].toUpperCase()).slice(0, 2).map(w => w[0]).join("");
const savedSet = () => new Set(S.user ? S.accountSaved || [] : JSON.parse(localStorage.getItem("ac-saved") || "[]"));
function storeSaved(s) {
  if (!S.user) { localStorage.setItem("ac-saved", JSON.stringify([...s])); return; }
  const before = new Set(S.accountSaved || []), adds = [...s].filter(x => !before.has(x)), dels = [...before].filter(x => !s.has(x));
  S.accountSaved = [...s];
  Promise.all([...adds.map(id => api(`/api/account/saved/${encodeURIComponent(id)}`, { method: "POST" })),
    ...dels.map(id => api(`/api/account/saved/${encodeURIComponent(id)}`, { method: "DELETE" }))])
    .then(r => { if (r.length) S.accountSaved = r[r.length - 1].program_ids; })
    .catch(err => { S.accountSaved = [...before]; toast(`Couldn't update your account: ${err.message}`); });
}
const shortName = it => (SCHOOL[it.id] || it.school || it.university);
const DEFAULT_FILTERS = { q: "", status: "", state: "", stem: false, max: "", sort: "relevance", savedOnly: false };
const EV = {
  detailed: { label: "Detailed evidence", icon: "checkCircle", plain: "Key facts — cost, STEM status, tests and outcomes — are each supported by an official source." },
  partial: { label: "Partially verified", icon: "checkCircle", plain: "Some facts are supported by official sources; others weren't published or haven't been checked yet." },
  discovered: { label: "Discovered", icon: "search", plain: "We've confirmed the program exists on its official page, but haven't collected its facts yet." },
  unavailable: { label: "Retrieval unavailable", icon: "alert", plain: "The official site refused our automated collector, so nothing about this program is verified yet." },
};
const EV_PLAIN = { detailed: "Official sources for key facts", partial: "Limited information", discovered: "Limited information · facts not collected yet",
  unavailable: "Limited information · site couldn't be checked" };
const FACT_SHORT = { location: "Location", duration_months: "Duration", application_requirements: "Requirements", test_policy: "Test policy", tuition: "Tuition",
  cost_of_attendance: "Total cost", stem_designation: "STEM", employment_rate: "Employment", median_base_salary: "Salary", industry_breakdown: "Industries",
  function_breakdown: "Functions", international_employment: "Intl. outcomes", sponsorship: "Sponsorship", application_deadlines: "Deadlines" };
const linkLabel = l => (!l || !l.status ? "" : { ok: "", redirect_ok: "", blocked: " (blocks automated checks — opens normally in a browser)", broken: " (link broken)", unreachable: " (couldn't be reached by our checker)" }[l.status] ?? "");

async function renderExplore() {
  const f = S.explore = { ...DEFAULT_FILTERS, ...S.explore };
  delete f.tier;
  S.compare = S.compare || [];
  let meta = null, seq = 0, first = null, showAll = false;
  const isPrimary = it => it.evidence_status === "detailed";
  const filtersActive = () => !!(f.q || f.status || f.state || f.stem || num(f.max) || f.savedOnly);
  const moreBox = el("div");
  const grid = el("div", { class: "ex-grid", "aria-live": "polite" }), metaLine = el("div", { class: "ex-meta" }), active = el("div", { class: "active-row" }), tray = el("div");
  try { first = await api("/api/programs"); } catch { /* load() shows the error */ }
  const by = first?.counts?.by_evidence_status || {}, idx = first?.index || {};
  const deb = (() => { let t; return fn => { clearTimeout(t); t = setTimeout(fn, 200); }; })();
  const sortHelp = { relevance: "Strongest evidence first, then most verified facts", evidence: "Most verified facts first", cost: "Lowest published cost first · unknown cost last",
    name: "University A–Z", state: "By state · unknown location last" };

  const searchInput = el("input", { type: "search", "aria-label": "Search programs", placeholder: "Search schools, cities, states or career keywords — try “technology” or “Texas”",
    oninput: e => { f.q = e.target.value; deb(load); } });
  const statusSel = el("select", { "aria-label": "Evidence status", onchange: e => { f.status = e.target.value; load(); } },
    [["", "All programs"], ["detailed", "Official sources for key facts"], ["partial", "Limited information"], ["discovered", "Facts not collected yet"], ["unavailable", "Site couldn't be checked"]]
      .map(([v, t]) => el("option", { value: v, text: t })));
  const stateSel = el("select", { "aria-label": "State", onchange: e => { f.state = e.target.value; load(); } }, el("option", { value: "", text: "Any state" }),
    (first?.states || []).map(s => el("option", { value: s, text: s })));
  const maxIn = el("input", { type: "number", inputmode: "numeric", min: 1000, step: 1000, "aria-label": "Maximum yearly cost of attendance in USD", placeholder: "Max cost / yr (USD)",
    oninput: e => { f.max = e.target.value; deb(load); } });
  const sortSel = el("select", { "aria-label": "Sort by", onchange: e => { f.sort = e.target.value; load(); } },
    [["relevance", "Sort: Strongest evidence"], ["evidence", "Sort: Most verified facts"], ["cost", "Sort: Lowest verified cost"], ["name", "Sort: Name A–Z"], ["state", "Sort: State"]].map(([v, t]) => el("option", { value: v, text: t })));
  const stemBtn = el("button", { type: "button", class: "ftoggle", onclick: () => { f.stem = !f.stem; load(); } }, svgIcon("checkCircle"), "STEM verified");
  const savedBtn = el("button", { type: "button", class: "ftoggle", onclick: () => { f.savedOnly = !f.savedOnly; drawList(); } }, svgIcon("heart"), "Saved");
  const syncControls = () => {
    statusSel.value = f.status; stateSel.value = f.state; maxIn.value = f.max; sortSel.value = f.sort; searchInput.value = f.q;
    stemBtn.setAttribute("aria-pressed", f.stem ? "true" : "false"); savedBtn.setAttribute("aria-pressed", f.savedOnly ? "true" : "false");
    const chips = [];
    if (f.q) chips.push([`“${f.q}”`, () => { f.q = ""; }]);
    if (f.status) chips.push([EV[f.status].label, () => { f.status = ""; }]);
    if (f.state) chips.push([`State: ${f.state}`, () => { f.state = ""; }]);
    if (num(f.max)) chips.push([`Max ${fmtUSD(num(f.max))}/yr`, () => { f.max = ""; }]);
    if (f.stem) chips.push(["STEM verified", () => { f.stem = false; }]);
    if (f.savedOnly) chips.push(["Saved only", () => { f.savedOnly = false; }]);
    put(clear(active), chips.map(([t, undo]) => el("button", { type: "button", class: "achip", "aria-label": `Remove filter ${t}`, onclick: () => { undo(); load(); } },
      t, el("span", { class: "x", "aria-hidden": "true", text: "×" }))),
      chips.length ? el("button", { type: "button", class: "reset", onclick: () => { Object.assign(f, DEFAULT_FILTERS); load(); }, text: "Reset all" }) : null);
  };
  const drawTray = () => {
    clear(tray);
    if (!S.compare.length) return;
    const names = S.compare.map(id => (meta?.items || []).find(i => i.id === id)).filter(Boolean).map(shortName);
    put(tray, el("div", { class: "tray", role: "region", "aria-label": "Compare selection" },
      el("span", { text: `Compare ${S.compare.length}/3` }), el("div", { class: "chips2" }, names.map(n => el("span", { text: n }))),
      el("button", { class: "link", type: "button", onclick: () => { S.compare = []; drawTray(); drawList(); }, text: "Clear" }),
      el("button", { class: "btn btn-primary", type: "button", disabled: S.compare.length < 2 ? true : null, onclick: openCompare, text: S.compare.length < 2 ? "Pick one more" : "Compare now" })));
  };
  const drawList = () => {
    syncControls();
    if (!meta) return;
    const saved = savedSet();
    const items = f.savedOnly ? meta.items.filter(i => saved.has(i.id)) : meta.items;
    const primary = items.filter(isPrimary), others = items.filter(it => !isPrimary(it));
    const grouped = !filtersActive() && primary.length > 0;
    const shown = grouped ? primary : items;
    put(clear(metaLine), el("h2", { class: "ex-h", text: grouped ? "Programs with official sources for key facts" : filtersActive() ? `${items.length} matching program${items.length === 1 ? "" : "s"}` : "All programs" }),
      el("span", { class: "ex-sub", text: grouped ? "Cost, STEM status, test policy and outcomes each come from the school's own pages. Start your shortlist here."
        : `${sortHelp[f.sort]}.${(f.stem || num(f.max)) ? " Cost and STEM filters only match facts with official evidence." : ""}` }));
    clear(grid);
    if (!items.length) { put(grid, el("div", { class: "empty2" }, el("b", { text: f.savedOnly ? "No saved programs yet" : "No programs match" }),
      el("p", { class: "small", style: "margin:6px 0 12px", text: f.savedOnly ? "Tap the heart on any program to save it." : "Try removing a filter." }),
      el("button", { type: "button", class: "btn btn-secondary", onclick: () => { Object.assign(f, DEFAULT_FILTERS); load(); }, text: "Reset filters" }))); return; }
    put(grid, shown.map(it => card(it, saved)));
    clear(moreBox);
    if (grouped && others.length) {
      put(moreBox, el("div", { class: "ex3-more" },
        el("h2", { class: "ex-h", text: "More programs to review" }),
        el("p", { class: "ex-sub", text: "Limited information: some facts for these programs come from official pages, and the rest are marked “Needs confirmation”. Check them on the school's site before relying on them." }),
        showAll ? el("div", { class: "ex-grid" }, others.map(it => card(it, saved))) : null,
        el("button", { type: "button", class: "btn btn-secondary", "aria-expanded": showAll ? "true" : "false",
          onclick: () => { showAll = !showAll; drawList(); if (!showAll) moreBox.scrollIntoView({ block: "start" }); },
          text: showAll ? "Hide these programs" : "Show more programs" })));
    }
    drawTray();
  };
  const load = async () => {
    syncControls();
    const mine = ++seq, qs = new URLSearchParams();
    if (f.q) qs.set("q", f.q); if (f.status) qs.set("status", f.status); if (f.state) qs.set("state", f.state);
    if (f.stem) qs.set("stem_verified", "true"); if (num(f.max)) qs.set("max_cost", num(f.max)); qs.set("sort", f.sort);
    let res;
    try { res = await api(`/api/programs?${qs}`); } catch (e) { if (mine === seq) put(clear(grid), el("div", { class: "empty2", text: `Could not load programs: ${e.message}` })); return; }
    if (mine !== seq) return;
    meta = res; drawList();
  };
  function card(it, saved) {
    const st = it.evidence_status, ev = EV[st], where = [it.city, it.state].filter(Boolean).join(", ") || "Location not confirmed";
    const coa = it.cost_of_attendance, est = it.costs?.estimate_annual, emp = it.employment;
    const cost = coa ? `${fmtUSD(coa.value)} a year · Official source` : est ? `About ${fmtUSD(est.value)} a year · ${est.publisher} estimate`
      : it.tuition ? `Tuition ${fmtUSD(it.tuition.value)} a year · total cost needs confirmation` : "Total cost · Needs confirmation";
    const stem = it.stem_designated === true ? (it.stem_partial ? "STEM-designated tracks · Official source" : "STEM-designated · Official source") : "STEM status · Needs confirmation";
    const job = emp ? `${emp.rate}% employed · ${emp.period} · Official source` : "Employment outcomes · Needs confirmation";
    const sig = (icon, text, known) => el("li", { class: known ? "" : "unk" }, svgIcon(icon), el("span", { text }));
    return el("article", { class: `pc2 ev-${st}` },
      el("div", { class: "pc2-head" }, el("h3", { text: shortName(it) }), el("div", { class: "pc2-where", text: where })),
      el("div", { class: `pc2-ev ev-${st}`, title: ev.plain }, el("span", { class: "dot", "aria-hidden": "true" }), EV_PLAIN[st] || ev.label),
      el("ul", { class: "pc2-sig" }, sig("dollar", cost, !!(coa || est || it.tuition)), sig("shield", stem, it.stem_designated === true), sig("chart", job, !!emp)),
      el("div", { class: "pc2-acts" },
        el("button", { type: "button", class: "btn btn-secondary btn-sm", onclick: () => openDetails(it.id) }, "Details"),
        it.official_link ? el("a", { class: "pc2-link", href: it.official_link.url, target: "_blank", rel: "noopener noreferrer" }, "Official page ↗") : null));
  }

  put($main,
    el("section", { class: "ex-top ex2-top" }, el("div", { class: "wrap ex2" },
      el("h1", { text: "Explore MBA programs" }),
      el("p", { class: "ex2-lead", text: "Search, filter and compare US full-time MBA programs. Every fact links to the official page it came from." }),
      el("div", { class: "ex-search" }, svgIcon("search"), searchInput),
      el("div", { class: "ex2-filters", role: "group", "aria-label": "Filters" },
        el("div", { class: "fsel" }, statusSel), el("div", { class: "fsel" }, stateSel), el("div", { class: "fsel" }, sortSel), stemBtn,
        el("details", { class: "ex2-more" }, el("summary", { text: "More filters" }), el("div", { class: "ex2-more-body" }, el("div", { class: "fsel" }, maxIn), savedBtn))),
      active,
      el("div", { class: "ex3-note" },
        el("p", {}, el("span", { class: "dot", "aria-hidden": "true" }),
          `${by.detailed ?? "Some"} programs have official sources for every key fact and are shown first. Others have limited information — anything not confirmed is marked “Needs confirmation”, never filled in.`),
        el("details", { class: "ex3-details" }, el("summary", { text: "Evidence details" }),
          el("div", { class: "ex3-details-body" },
            el("ul", {},
              el("li", {}, el("b", { text: `${by.detailed ?? "—"} detailed evidence` }), " — cost, STEM status, test policy and outcomes each supported by an official source."),
              el("li", {}, el("b", { text: `${by.partial ?? "—"} partially verified` }), " — some facts from official pages; the rest weren't published or haven't been checked."),
              el("li", {}, el("b", { text: `${(by.discovered ?? 0) + (by.unavailable ?? 0)} discovered only` }), ` (${by.discovered ?? 0} with facts not yet collected, ${by.unavailable ?? 0} whose site couldn't be checked) — these programs were discovered from official university pages, but we have not verified enough facts to use them in detailed recommendations.`)),
            el("p", { text: "Sample analyses use only the programs with detailed evidence. A personal analysis can include any program with official facts; facts that aren't verified are shown as needing confirmation." }),
            el("button", { type: "button", class: "linkbtn", onclick: () => openLegend(), text: "What do evidence levels mean?" })))))),
    el("section", { class: "ex2-list" }, el("div", { class: "wrap ex2" }, metaLine, grid, moreBox,
      el("p", { class: "ex-foot", text: "Employment rates use each school's own definition and graduating class, so they aren't directly comparable — Details shows each definition. Save and compare programs from Details." }))),
    tray);
  load();

  function openLegend() {
    openDrawer(el("div", {}, el("span", { class: "status ev-partial", text: "Evidence levels" }), el("h2", { text: "How to read evidence labels" })),
      el("div", { class: "drawer-body" }, el("div", { class: "legend2" },
        ...Object.entries(EV).map(([k, v]) => el("div", {}, el("span", { class: `status ev-${k}`, style: "flex:none" }, svgIcon(v.icon), v.label), el("span", { text: v.plain }))),
        el("div", {}, el("span", { class: "tagline chk", style: "flex:none", text: "Not published" }), el("span", { text: "We checked the official pages and this fact isn't stated there." })),
        el("div", {}, el("span", { class: "tagline nchk", style: "flex:none", text: "Not checked yet" }), el("span", { text: "We haven't looked for this fact yet. It may well be published." }))),
        el("p", { class: "small muted", style: "margin-top:20px", text: "A page loading is not the same as a fact being verified: a program is only upgraded when specific facts are supported by quoted official sources." })));
  }

  async function openDetails(id) {
    let d;
    try { d = await api(`/api/programs/${encodeURIComponent(id)}`); } catch (e) { toast(e.message); return; }
    const it = d.item, st = it.evidence_status, ev = EV[st];
    if (it.tier === "verified") setChatContext({ ...S.ctx, program_id: id, compare_ids: [] });
    const body = el("div", { class: "drawer-body" });
    const official = it.official_link ? el("a", { class: "btn btn-secondary", href: it.official_link.url, target: "_blank", rel: "noopener noreferrer" }, "Visit official program page ↗") : null;
    const isSaved = savedSet().has(id), inCmp = S.compare.includes(id);
    put(body, el("div", { class: "ex2-dacts" },
      el("button", { type: "button", class: "btn btn-quiet", "aria-pressed": isSaved ? "true" : "false", onclick: e => { const s2 = savedSet(); s2.has(id) ? s2.delete(id) : s2.add(id); storeSaved(s2);
        const on = s2.has(id); e.currentTarget.setAttribute("aria-pressed", on); e.currentTarget.textContent = on ? "Saved on this device ✓" : "Save program"; toast(on ? `Saved ${shortName(it)} on this device` : `Removed ${shortName(it)}`); if (f.savedOnly) drawList(); },
        text: isSaved ? "Saved on this device ✓" : "Save program" }),
      el("button", { type: "button", class: "btn btn-quiet", disabled: !inCmp && S.compare.length >= 3 ? true : null, onclick: e => { S.compare = S.compare.includes(id) ? S.compare.filter(x => x !== id) : [...S.compare, id].slice(0, 3);
        e.currentTarget.textContent = S.compare.includes(id) ? "Remove from comparison" : "Add to comparison"; drawTray(); },
        text: inCmp ? "Remove from comparison" : S.compare.length >= 3 ? "Comparison is full (3)" : "Add to comparison" })));
    put(body, el("div", { class: `callout2 ${st === "detailed" ? "ok" : st === "unavailable" ? "" : "info"}` }, svgIcon(ev.icon), el("span", { text: ev.plain })));
    if (it.ranking) put(body, el("div", { class: "dsec" }, el("h3", { text: "Ranking (context only)" }), rankLine(it.ranking, true)));
    if (d.facts) {
      const F = Object.fromEntries(d.facts.map(x => [x.fact, x]));
      const box = (label, fct, fmt, extra) => {
        const ok = fct && fct.status === "verified";
        return el("div", { class: `dfact ${ok ? "ok" : fct && fct.checked === false ? "notchecked" : "unk"}` }, el("div", { class: "k", text: label }),
          el("div", { class: "v", text: ok ? fmt(fct.value) : "—" }),
          ok ? el("div", { class: "d", text: [fct.period, extra ? extra(fct) : null].filter(Boolean).join(" · ") })
            : el("span", { class: `tagline ${fct && fct.checked === false ? "nchk" : "chk"}`, text: fct && fct.checked === false ? "Not checked yet" : "Not stated on the official pages checked" }),
          !ok && fct?.note?.startsWith("Not verified:") ? el("div", { class: "d", text: fct.note.replace(/ Candidate value.*$/, "") }) : null);
      };
      put(body,
        el("div", { class: "dsec" }, el("h3", { text: "Costs" }), costRows(it.costs)),
        researchBlocks(d.research),
        el("div", { class: "dsec" }, el("h3", { text: "Program facts" })),
        el("div", { class: "dgrid", style: "margin-top:8px" },
          box("STEM designation", F.stem_designation, x => (x.designated ? (it.stem_partial ? "Some tracks only" : "Designated") : "Not designated"), x => x.value.scope),
          box("Employment rate", F.employment_rate, x => `${x}%`, x => x.definition),
          box("Median base salary", F.median_base_salary, fmtUSD, x => x.definition),
          box("Test policy", F.test_policy, x => (String(x).length > 80 ? String(x).slice(0, 78) + "…" : String(x))),
          d.research?.facts.some(f => f.field === "application_deadlines") ? null : box("Application deadlines", F.application_deadlines, x => `${x.length} rounds`, x => x.value.slice(0, 2).join(" · ")),
          box("Employer visa sponsorship", F.sponsorship, x => x.employer)),
        d.h1b_history ? el("div", { class: "dsec" }, el("h3", { text: "Historical H-1B filings by employers that hired graduates" }), h1bBlock(d.h1b_history, { limit: 8 })) : null,
        F.sponsorship?.status !== "verified" ? el("div", { class: "callout2", style: "margin-top:14px" }, svgIcon("alert"),
          el("span", { text: "No employer-specific sponsorship evidence. Employer lists in employment reports are not proof that a company sponsors visas." })) : null,
        it.career_keywords.length ? el("div", { class: "dsec" }, el("h3", { text: "Reported hiring industries & functions" }),
          el("div", { class: "row", style: "gap:6px" }, [...new Set(it.career_keywords.map(k => k.keyword))].map(k => el("span", { class: "fitdot", text: k })))) : null,
        el("div", { class: "dsec" }, el("h3", { text: "Sources for each fact" }),
          d.facts.filter(x => x.evidence?.length).map(x => { const e = x.evidence[0];
            return el("div", { class: "srcrow" },
              el("div", { class: "spread" }, el("b", { text: FACT_LABEL[x.fact] || FACT_SHORT[x.fact] || x.fact }),
                el("span", { class: `status ${e.rechecked ? "ev-detailed" : "ev-partial"}`, text: e.rechecked ? "Re-checked by hand" : "Collected from source" })),
              el("div", { class: "q", text: `“${e.excerpt}”` }),
              el("div", { class: "m" }, extLink((e.link && e.link.final_url) || e.source_url, e.source_title), ` · accessed ${e.checked_on}${e.excerpt_is_paraphrase ? " · paraphrased" : ""}${linkLabel(e.link)}`)); })),
        el("div", { class: "dsec row" }, official, el("a", { class: "btn btn-primary", href: "#/start" }, "Check my career fit ", arrow())));
    } else {
      put(body,
        el("div", { class: "dgrid", style: "margin-top:16px" },
          el("div", { class: "dfact" }, el("div", { class: "k", text: "Program" }), el("div", { class: "v", text: it.program_name })),
          el("div", { class: `dfact ${it.city ? "" : "unk"}` }, el("div", { class: "k", text: "Location" }), el("div", { class: "v", text: [it.city, it.state].filter(Boolean).join(", ") || "—" }),
            it.city ? el("div", { class: "d", text: it.location_basis }) : el("span", { class: "tagline nchk", text: "Not confirmed" })),
          ...["STEM designation", "Employment outcomes", "Visa sponsorship"].map(k => el("div", { class: "dfact notchecked" }, el("div", { class: "k", text: k }), el("div", { class: "v", text: "—" }),
            el("span", { class: "tagline nchk", text: "Not checked yet" })))),
        el("div", { class: "dsec" }, el("h3", { text: "Costs" }), costRows(it.costs)),
        researchBlocks(d.research),
        it.excerpt ? el("div", { class: "dsec" }, el("h3", { text: "From the official page" }), el("p", { class: "small", style: "color:var(--text-2)", text: `“${it.excerpt}”` })) : null,
        el("div", { class: "dsec" }, official,
          el("div", { class: "xs muted", style: "margin-top:8px", text: `Link checked ${it.official_link?.checked_at?.slice(0, 10) || "—"}: ${it.official_link?.status === "blocked" ? "the site refuses automated checks but opens in a browser" : it.official_link?.status === "ok" ? "page reachable" : it.official_link?.status || "not checked"} · discovered ${it.discovered_on}` })));
    }
    const color = LOGO_COLORS[[...it.id].reduce((a, ch) => a + ch.charCodeAt(0), 0) % LOGO_COLORS.length];
    openDrawer(el("div", { class: "row", style: "gap:14px;align-items:center" },
      el("div", { class: "logo", style: `background-color:${it.tier === "verified" ? color : "#ECFEFF"};${it.tier === "verified" ? "" : "color:#0E7490"}`, "aria-hidden": "true", text: initials(shortName(it)) || "MBA" }),
      el("div", {}, el("span", { class: `status ev-${st}` }, svgIcon(ev.icon), ev.label), el("h2", { text: shortName(it) }),
        el("div", { class: "small muted", text: `${it.university} · ${it.program_name}` }))), body);
  }

  async function openCompare() {
    let rows;
    setChatContext({ ...S.ctx, program_id: null, compare_ids: S.compare.slice(0, 4) });
    try { rows = await Promise.all(S.compare.map(id => api(`/api/programs/${encodeURIComponent(id)}`))); } catch (e) { toast(e.message); return; }
    const val = (d, fact, fmt) => {
      if (!d.facts) return [null, "Not checked yet"];
      const x = d.facts.find(z => z.fact === fact);
      return x && x.status === "verified" ? [fmt(x), null] : [null, x && x.checked === false ? "Not checked yet" : "Not stated (official pages checked)"];
    };
    const supp = (d, ...fields) => { const f = (d.research?.facts || []).find(x => fields.includes(x.field));
      if (f) return [`${fmtSupp(f)}${f.period && f.unit !== "dates" ? ` · ${f.period}` : ""}${f.field === "class_avg_gmat" ? " (average)" : f.field === "class_median_gmat" ? " (median)" : ""}`, null];
      const g = (d.research?.gaps || []).find(x => fields.includes(x.field)); return [null, g ? g.reason : "Not researched yet"]; };
    const spec = [
      ["Evidence", d => [EV[d.item.evidence_status].label, null]],
      ["Location", d => { const w = [d.item.city, d.item.state].filter(Boolean).join(", "); return w ? [w, null] : [null, "Not confirmed"]; }],
      ["Total cost / yr", d => val(d, "cost_of_attendance", x => `${fmtUSD(x.value)} (${x.period})`)],
      ["Tuition / yr", d => val(d, "tuition", x => `${fmtUSD(x.value)} (${x.period})`)],
      ["Estimated one-year cost (third party)", d => { const e = d.item.costs?.estimate_annual; return e ? [`${fmtUSD(e.value)} · ${e.publisher} estimate · ${e.period}`, null] : [null, "No estimate found"]; }],
      ["Class size", d => supp(d, "class_size")],
      ["GMAT (median or average)", d => supp(d, "class_median_gmat", "class_avg_gmat")],
      ["International students", d => supp(d, "class_pct_international")],
      ["Deadlines (official, 2026–27 cycle)", d => supp(d, "application_deadlines")],
      ["STEM designation", d => val(d, "stem_designation", x => (x.value.designated ? (d.item.stem_partial ? `Some tracks: ${x.value.scope}` : "Designated") : "Not designated"))],
      ["Employment rate*", d => val(d, "employment_rate", x => `${x.value}% · ${x.period} · ${x.definition}`)],
      ["Median base salary", d => val(d, "median_base_salary", x => `${fmtUSD(x.value)} · ${x.period}`)],
      ["Test policy", d => val(d, "test_policy", x => x.value)],
      ["Deadlines", d => val(d, "application_deadlines", x => x.value.join(" · "))],
      ["Employer sponsorship", d => val(d, "sponsorship", x => `${x.value.employer}: ${x.value.statement}`)],
    ];
    const table = el("table", { class: "cmp-table" },
      el("thead", {}, el("tr", {}, el("th", { scope: "col", text: "" }), rows.map(d => el("th", { scope: "col", text: shortName(d.item) })))),
      el("tbody", {}, spec.map(([label, fn]) => el("tr", {}, el("th", { scope: "row", text: label }),
        rows.map(d => { const [ok, unk] = fn(d); return el("td", { class: ok ? (label === "Evidence" ? "" : "ok") : "unk", text: ok || unk }); })))));
    openDrawer(el("div", {}, el("span", { class: "status ev-partial", text: "Side by side" }), el("h2", { text: "Compare programs" })),
      el("div", { class: "drawer-body" }, el("div", { class: "cmp-wrap" }, table),
        el("p", { class: "xs muted", style: "margin-top:14px", text: "* Employment rates keep each school's own definition and are never ranked. “Not published” = we checked the official pages and it isn't stated; “Not checked yet” = we haven't looked for it." })), true);
  }
}

function openDrawer(headContent, body, wide = false) {
  const root = document.getElementById("modal-root");
  const opener = document.activeElement;
  const close = () => { clear(root); document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; opener?.focus?.(); };
  const onKey = e => { if (e.key === "Escape") close(); };
  const closeBtn = el("button", { class: "close-btn", type: "button", "aria-label": "Close", onclick: close, text: "×" });
  put(clear(root), el("div", { class: "drawer-bg", onclick: close }),
    el("div", { class: `drawer${wide ? " wide" : ""}`, role: "dialog", "aria-modal": "true", "aria-label": wide ? "Compare programs" : "Program details" },
      el("div", { class: "drawer-head" }, headContent, closeBtn), body));
  document.addEventListener("keydown", onKey);
  document.body.style.overflow = "hidden";
  closeBtn.focus();
}


/* ---------------- research layer (Step 14): official facts, reported figures and estimates, always labeled ---------------- */
const KIND_TAG = { official: ["ok", "Official"], reported: ["", "Reported"], estimate: ["warn", "Estimate"] };
const BASIS_TEXT = { annual: "per year", full_program: "whole program", semester: "per semester", cohort: "", cycle: "" };
function fmtSupp(f) {
  const v = f.value;
  if (f.unit === "USD") return fmtUSD(v);
  if (f.unit === "percent") return `${v}%`;
  if (f.unit === "dates" && Array.isArray(v)) return v.map(x => `${x.round}: ${x.deadline}`).join(" · ");
  return String(v);
}
function costRows(costs) {
  if (!costs || !costs.lines.length) return el("p", { class: "small muted", text: "No sourced cost figures yet — check the official tuition page." });
  return el("div", { class: "costrows" }, costs.lines.map(l => { const [cls, tag] = KIND_TAG[l.kind];
    return el("div", { class: `costrow ${l.kind}` },
      el("div", { class: "cr-main" }, el("span", { class: "cr-label", text: l.label }), el("span", { class: `pvtag ${cls}`, text: tag })),
      el("div", { class: "cr-val" }, el("b", { text: fmtUSD(l.value) }), ` ${BASIS_TEXT[l.period_basis] || ""}${l.period ? ` · ${l.period}` : ""}`),
      el("div", { class: "cr-src xs muted" }, l.source_url ? extLink(l.source_url, l.publisher || "Source") : (l.publisher || ""), l.notes ? ` · ${l.notes}` : ""));
  }),
  el("p", { class: "xs muted", text: "These measure different things — official tuition, official cost of attendance, figures reported by third parties, and third-party estimates — so they aren't combined or treated as contradictions." }));
}
const RESEARCH_GROUPS = [["Employment outcomes", ["employment_rate", "median_base_salary"]], ["Class profile", ["class_size", "class_median_gmat", "class_avg_gmat", "class_pct_international"]],
  ["Scholarships and fellowships", ["scholarships"]], ["Application deadlines", ["application_deadlines"]]];
function researchBlocks(r) {
  if (!r) return null;
  const facts = r.facts.filter(f => !["tuition", "mandatory_fees", "tuition_and_fees", "cost_of_attendance", "reported_cost_of_attendance", "est_annual_cost", "est_two_year_cost"].includes(f.field));
  const groups = RESEARCH_GROUPS.map(([title, fields]) => [title, facts.filter(f => fields.includes(f.field))]).filter(([, xs]) => xs.length);
  return [
    groups.map(([title, xs]) => el("div", { class: "dsec" }, el("h3", { text: title }),
      el("div", { class: "dgrid" }, xs.map(f => el("div", { class: "dfact ok" }, el("div", { class: "k", text: f.label }),
        el("div", { class: `v${f.unit === "text" || f.unit === "dates" ? " vtext" : ""}`, text: fmtSupp(f) }),
        el("div", { class: "d" }, [f.period, f.source_type === "official" ? "official page" : `reported by ${f.publisher}`].filter(Boolean).join(" · "), " · ", extLink(f.source_url, "Source"),
          f.notes ? el("div", { class: "xs muted", text: f.notes }) : null)))))),
    r.gaps.length ? el("details", { class: "dsec gaps" }, el("summary", { text: `Open research questions (${r.gaps.length})` }),
      el("ul", { class: "small" }, r.gaps.map(g => el("li", {}, el("b", { text: `${g.label}: ` }), g.reason, g.source_url ? [" — ", extLink(g.source_url, "page checked")] : null)))) : null];
}


/* Historical employer H-1B evidence (DOL LCA). Never presented as a promise of sponsorship. */
const OCC_LABEL = { management_consulting: "management consulting", product_management: "product management", corporate_finance_strategy: "corporate finance / strategy" };
function h1bBlock(h, opts = {}) {
  if (!h) return null;
  const note = el("p", { class: "xs h1b-note", text: h.note });
  if (h.status !== "ok") return el("div", { class: "h1b" }, el("p", { class: "small muted", text: h.reason || "No employer evidence for this program." }), note);
  const withFilings = h.employers.filter(e => e.total_filings > 0).slice(0, opts.limit || 6);
  const scope = [h.occupation ? OCC_LABEL[h.occupation] : "all three target occupations", h.metro || "all five cities"].join(" · ");
  const src = h.data_source || {};
  return el("div", { class: "h1b" },
    el("p", { class: "small" }, `Employers that the school's official report says hired its graduates, with their certified H-1B labor condition applications (FY${src.fiscal_year}, ${scope}). `,
      extLink(h.school_list.source_url, "School list"), " · ", extLink(src.source_page, "DOL data")),
    withFilings.length ? el("ul", { class: "dlist" }, withFilings.map(e => el("li", {},
      el("b", { text: e.employer }), ` — ${e.total_filings} filing${e.total_filings === 1 ? "" : "s"}`,
      el("div", { class: "xs muted", text: e.filings.slice(0, 3).map(f => `${f.filings} · ${OCC_LABEL[f.occupation]} · ${f.metro}`).join("; ") }))))
      : el("p", { class: "small muted", text: "None of the listed employers have matching filings for this occupation and city." }),
    h.employers.length > withFilings.length || h.unmatched_school_employers.length ? el("p", { class: "xs muted",
      text: `${h.employers.filter(e => !e.total_filings).length} listed employers had no matching filings; ${h.unmatched_school_employers.length} couldn't be matched to DOL employer names and are left unmatched.` }) : null,
    note);
}


/* Prestige ranking as CONTEXT only (Poets&Quants composite); never used for matching or sorting. */
function rankLine(r, full) {
  if (!r) return null;
  const txt = r.rank ? `#${r.rank} · ${r.source} U.S. MBA ranking, ${r.edition}` : `${r.source} U.S. MBA ranking: not ranked in this source`;
  return el("div", { class: `rankline${full ? " full" : ""}` }, el("span", { class: "rk" }, txt),
    full && r.source_url ? [" · ", extLink(r.source_url, "Source")] : null, el("div", { class: "rk-note", text: r.note }));
}

/* ---------------- how it works ---------------- */
/* ---------------- International applicants (dedicated page) ----------------
   Explains what AdmitCompass checks for applicants who will need U.S. work authorization. Counts come from the
   catalog API; no legal advice, visa guarantees, admission odds or sponsorship claims. */
async function renderIntl() {
  const counts = el("dl", { class: "pg-facts" });
  const topic = (icon, h, what, source, unknown) => el("section", { class: "pg-topic" },
    el("div", { class: "pg-topic-h" }, el("span", { class: "pg-ic" }, svgIcon(icon)), el("h3", { text: h })),
    el("p", { text: what }),
    el("dl", { class: "pg-kv" }, el("div", {}, el("dt", { text: "Where it comes from" }), el("dd", { text: source })),
      el("div", {}, el("dt", { text: "When it isn't known" }), el("dd", { text: unknown }))));
  put($main, el("div", { class: "pg" },
    el("header", { class: "pg-hero" }, el("div", { class: "wrap pg-narrow" },
      el("span", { class: "kicker", text: "For international applicants" }),
      el("h1", { text: "Plan an MBA when you'll need U.S. work authorization" }),
      el("p", { class: "pg-lead", text: "STEM status, total cost, employer sponsorship history and international outcomes decide whether a program is realistic for you. AdmitCompass shows what official sources say about each one — and marks clearly what isn't known." }),
      el("div", { class: "pg-cta" }, el("a", { class: "btn btn-primary btn-lg", href: "#/start" }, "Start my personalized pathway ", arrow()),
        el("a", { class: "btn btn-quiet", href: "#/dashboard/demo", text: "See a sample analysis for an applicant from India" })),
      counts)),
    el("div", { class: "wrap pg-narrow" },
      el("section", { class: "pg-sec" }, el("h2", { text: "What we check for you" }),
        topic("shield", "STEM designation", "Whether the MBA — or only some tracks — is STEM-designated, with the exact scope the school states.",
          "The program's official page.", "Shown as “Needs confirmation”. STEM designation is a program classification, not a visa or sponsorship guarantee."),
        topic("dollar", "Total cost, not tuition alone", "Your budget is compared with the school's published one-year cost of attendance, which includes living costs — never with tuition alone.",
          "The school's official cost page. Third-party estimates are labeled with their publisher.", "No comparison is made; tuition is shown separately and marked as tuition only."),
        topic("globe", "Employer sponsorship history", "For employers that a school's official report says hired its graduates, the number of certified H-1B labor condition applications they filed.",
          "U.S. Department of Labor H-1B disclosure data (fiscal year 2025), matched only to employers on the school's own list.", "Shown as unknown. Past filings show what employers did, not what they will do — never a promise of sponsorship."),
        topic("chart", "International employment outcomes", "Outcome figures for international students, kept with their cohort and definition.",
          "The school's official employment report.", "Shown as “Not published” — most schools don't publish a separate figure, so ask the career office.")),
      el("section", { class: "pg-sec" }, el("h2", { text: "Three kinds of information, kept apart" }),
        el("ol", { class: "pg-kinds" },
          el("li", {}, el("b", { text: "School facts" }), el("span", { text: " — from official university pages, with the page link and the date we checked it." })),
          el("li", {}, el("b", { text: "Employer filing history" }), el("span", { text: " — from U.S. Department of Labor data. It describes employers, not schools, and it's history, not a guarantee." })),
          el("li", {}, el("b", { text: "Unknown" }), el("span", { text: " — not on the official pages we checked. We never fill these in; you'll see what to confirm and where." })))),
      el("section", { class: "pg-sec pg-limits" }, el("h2", { text: "What AdmitCompass won't do" }),
        el("p", { text: "It doesn't give legal or immigration advice, guarantee a visa or sponsorship, or estimate your chances of admission. For questions about your own visa or work-authorization eligibility, ask the school's international student office (DSO) or a qualified immigration attorney." })),
      el("section", { class: "pg-sec pg-end" }, el("h2", { text: "See your options with the evidence attached" }),
        el("a", { class: "btn btn-primary btn-lg", href: "#/start" }, "Start my personalized pathway ", arrow())))));
  try {
    const r = await api("/api/programs"), core = r.items.filter(i => i.tier === "verified");
    put(counts,
      el("div", {}, el("dt", { text: "Programs with STEM status from an official page" }), el("dd", { text: `${core.filter(i => i.stem_designated === true).length} of ${core.length}` })),
      el("div", {}, el("dt", { text: "Programs with an official total cost" }), el("dd", { text: `${core.filter(i => i.cost_of_attendance).length} of ${core.length}` })));
  } catch { counts.remove(); }
}

/* ---------------- How it works ---------------- */
const AGENT_FLOW = [
  ["Pathway Matcher", "Turns your goal into target roles and shortlists programs by where they lead.", "A shortlist built on career fit"],
  ["Evidence Analyst", "Checks cost, STEM status, outcomes and employer filings against official sources.", "Verified facts, with unknowns marked"],
  ["Strategy Planner", "Turns your gaps and the evidence into a test decision and a weekly plan.", "A GRE-or-GMAT decision and weekly actions"],
  ["Skeptic", "Challenges weak evidence, budget assumptions and immigration overstatements.", "Corrections — at most one revision"],
];
async function renderHow() {
  const data = el("div", {}, el("p", { class: "muted", text: "Loading…" }));
  put($main, el("div", { class: "pg" },
    el("header", { class: "pg-hero pg-hero-light" }, el("div", { class: "wrap pg-narrow" },
      el("span", { class: "kicker", text: "How it works" }),
      el("h1", { text: "From your career goal to a plan you can act on" }),
      el("p", { class: "pg-lead", text: "You share your background, goal, budget and time. AdmitCompass returns a shortlist, a GRE-or-GMAT decision and a weekly plan — and plain code checks every fact against official sources before you see it." }),
      el("div", { class: "pg-cta" }, el("a", { class: "btn btn-primary btn-lg", href: "#/start" }, "Find my pathway ", arrow()),
        el("a", { class: "btn btn-quiet", href: "#/dashboard/demo", text: "See a sample analysis" })))),
    el("div", { class: "wrap pg-narrow" },
      el("section", { class: "pg-sec" }, el("h2", { text: "Four agents, one job each" }),
        el("ol", { class: "pg-flow" }, AGENT_FLOW.map(([n, job, out], i) => el("li", {},
          el("span", { class: "num", text: String(i + 1) }),
          el("div", {}, el("h3", { text: n }), el("p", { text: job }), el("p", { class: "pg-out" }, el("b", { text: "Output: " }), out))))),
        el("p", { class: "pg-note", text: "The agents read only from AdmitCompass's evidence store. They can't add a fact of their own." })),
      el("section", { class: "pg-sec" }, el("h2", { text: "Technical details" }),
        panel("What the code guarantees", "how-guarantees", el("ul", { class: "ticks" },
          el("li", { text: "Program facts come only from the evidence store; a model can't create a verified fact." }),
          el("li", { text: "Every verified claim cites an evidence id, and any number in it must appear in that evidence." }),
          el("li", { text: "STEM, sponsorship and budget status are recomputed from the store and corrected if a model disagrees." }),
          el("li", { text: "Employment numbers are compared only when cohort and definition match." }),
          el("li", { text: "Questions about admission chances or your own visa eligibility are answered with a referral, not a guess, before any model is called." }),
          el("li", { text: "Each run is capped at 25 model requests, 200,000 tokens and 300 seconds, with at most one Skeptic revision." }))),
        panel("What's in the data", "how-data", data),
        panel("Evidence and safety for reviewers", "how-review", el("div", {},
          el("p", { text: "Every analysis keeps its Skeptic review, citations, usage and a technical trace. The sample analysis also has a safety test mode and an exportable run record." }),
          el("a", { class: "btn btn-quiet", href: "#/results/demo/evidence", text: "Open the sample's evidence and trace" })))))));
  try {
    const r = await api("/api/programs"), by = r.counts.by_evidence_status, idx = r.index || {};
    put(clear(data),
      el("p", { text: `${r.total} US full-time MBA programs: ${by.detailed} with detailed evidence, ${by.partial} partially verified, and ${(by.discovered || 0) + (by.unavailable || 0)} not yet checked.${idx.built_on ? ` Facts were collected from official university pages (index built ${idx.built_on}).` : ""}` }),
      el("p", { text: "A fact is “verified” only when an official source supports it; anything else is shown as unknown and is never filled in. Programs that are only discovered — we know they exist and where — aren't used by the agents until their facts are collected." }));
  } catch { put(clear(data), el("p", { text: "The data summary couldn't be loaded." })); }
}

/* ---------------- live run ---------------- */
/* Public errors are structured objects {status, message, error_code}; older payloads may still carry a string. */
const errText = e => (e == null ? "" : typeof e === "string" ? e : e.message || "");
function describeEvent(e) {
  const d = e.detail || {};
  switch (e.kind) {
    case "agent_start": return d.revision_feedback ? "Revising with the Skeptic's feedback" : "Started";
    case "llm_call": return `Model call — ${d.tool_calls_requested ? `asked for ${d.tool_calls_requested} lookup(s)` : "answered"} · ${fmtInt(d.input_tokens)} in / ${fmtInt(d.output_tokens)} out tokens`;
    case "tool_call": {
      let a = d.args; if (typeof a === "string") { try { a = JSON.parse(a); } catch { /* keep */ } }
      const s = a && typeof a === "object" ? Object.entries(a).map(([k, v]) => `${k}=${Array.isArray(v) ? v.join(",") : v}`).join(" ") : "";
      return `Looked up ${d.tool}(${s.slice(0, 120)})${d.cached_repeat ? " · from cache" : ""}${d.ok === false ? ` · ${errText(d.error) || "lookup failed"}` : ""}`;
    }
    case "validation": return d.ok ? "Answer passed format checks" : "Answer failed format checks — retrying";
    case "grounding":
      if (d.retry) return `Evidence check found problems — ${d.mode === "repair" ? "one repair request" : "retrying"}`;
      if ("violations_after_retry" in d) return `Evidence check after repair: ${d.violations_after_retry} issue(s)`;
      return d.violations ? `Evidence check flagged ${d.violations} issue(s)` : "Evidence check passed";
    case "handoff": return `Handed over to ${AGENT_NAME[d.to] || d.to}`;
    case "revision": return `Skeptic asked for a revision of ${AGENT_NAME[d.target] || d.target}`;
    case "budget_stop": return `Stopped by the budget limit: ${d.reason}`;
    case "agent_failure": return errText(d.error) || "Stopped safely";
    case "run_end": return `Finished · ${d.requests} model requests · ${fmtInt(d.total_tokens)} tokens`;
    default: return e.kind;
  }
}
const isBad = e => { const d = e.detail || {}; return (e.kind === "validation" && !d.ok) || (e.kind === "grounding" && (d.violations || d.retry || d.violations_after_retry)) || e.kind === "budget_stop" || e.kind === "agent_failure"; };
const feedItem = e => el("li", { class: isBad(e) ? "bad" : "" }, el("span", { class: "seq", text: `#${e.seq}` }), el("span", { class: "who", text: AGENT_NAME[e.agent] || e.agent }), el("span", { text: describeEvent(e) }));
function agentStates(events) {
  const st = Object.fromEntries(AGENTS.map(a => [a.id, "waiting"])); let cur = null;
  for (const e of events) {
    if (e.kind === "agent_start" && st[e.agent]) { st[e.agent] = "running"; cur = e.agent; }
    if (e.kind === "handoff" && st[e.agent]) st[e.agent] = "done";
    if (e.kind === "grounding" && e.agent === "skeptic") st.skeptic = "done";
    if ((e.kind === "budget_stop" || e.kind === "agent_failure") && cur && st[cur] === "running") st[cur] = "stopped";
  }
  return st;
}
function renderRun(runId) {
  const events = []; let since = 0, failures = 0;
  const title = el("h1", { text: "Your analysis is running" });
  const steps = el("ol", { class: "runsteps" }), current = el("p", { class: "small muted", "aria-live": "polite" }), meters = el("div", { class: "meterline" });
  const status = el("div"), feed = el("ol", { class: "feed" });
  put($main, el("div", { class: "wrap narrow onb" }, title,
    el("p", { class: "why", text: "This usually takes 30–120 seconds. Progress comes from real backend events." }),
    status, steps, current, meters, el("div", { style: "margin-top:24px" }, more("Show activity log", feed))));
  const onLeave = e => { e.preventDefault(); e.returnValue = ""; };
  window.addEventListener("beforeunload", onLeave);
  const draw = r => {
    const st = agentStates(events);
    put(clear(steps), AGENTS.map(a => el("li", { class: st[a.id] }, el("span", { class: "ic", "aria-hidden": "true" }),
      el("div", {}, el("b", { text: a.name }), el("div", { class: "xs muted", text: a.desc })),
      el("span", { class: "xs muted", text: { waiting: "Waiting", running: "Working…", done: "Done", stopped: "Stopped" }[st[a.id]] }))));
    const last = events[events.length - 1]; current.textContent = last ? `${AGENT_NAME[last.agent] || last.agent}: ${describeEvent(last)}` : "Starting…";
    const req = events.filter(e => e.kind === "llm_call").length, tok = events.filter(e => e.kind === "llm_call").reduce((s, e) => s + (e.detail.input_tokens || 0) + (e.detail.output_tokens || 0), 0);
    put(clear(meters), el("span", { text: `${req} / ${r.budget?.max_requests ?? "—"} model requests` }), el("span", { text: `${fmtInt(tok)} tokens` }), el("span", { text: `${Math.round(r.elapsed_seconds || 0)} s` }));
  };
  async function tick() {
    try {
      const r = await api(`/api/runs/${encodeURIComponent(runId)}?since=${since}`); failures = 0;
      for (const e of r.events) { events.push(e); put(feed, feedItem(e)); }
      since = r.next_since; draw(r);
      if (r.status === "running") { S.poll = setTimeout(tick, 1200); return; }
      window.removeEventListener("beforeunload", onLeave);
      S.config = await api("/api/config").catch(() => S.config);
      if (r.result?.report?.recommendations?.length) {
        title.textContent = "Your analysis is ready"; S.result = r.result;
        put(clear(status), note("", "Done.", "Opening your shortlist…"));
        setTimeout(() => { location.hash = `#/dashboard/${runId}`; }, 800);
      } else {
        title.textContent = "The analysis stopped";
        put(clear(status), note("bad", r.status === "stopped_budget" ? "It reached its budget limit." : "It stopped safely.",
          el("span", {}, `${errText(r.error) || "No recommendations were produced."} Nothing was guessed to fill the gap. `, el("a", { href: "#/results/demo", text: "View the sample analysis" }))));
      }
    } catch (err) {
      if (++failures > 5) { put(clear(status), note("bad", "Lost contact with the server.", err.message)); window.removeEventListener("beforeunload", onLeave); return; }
      S.poll = setTimeout(tick, 2000);
    }
  }
  tick();
}

/* ---------------- results ---------------- */
const FACT_LABEL = { location: "Location", test_policy: "Test policy", tuition: "Tuition", cost_of_attendance: "Cost of attendance", stem_designation: "STEM designation",
  employment_rate: "Employment rate", median_base_salary: "Median base salary", international_employment: "International outcomes", sponsorship: "Employer sponsorship" };
function factValue(f) {
  if (f.status !== "verified") return "Unknown";
  const v = f.value;
  switch (f.fact) {
    case "location": return `${v.city}, ${v.state}`;
    case "tuition": case "cost_of_attendance": case "median_base_salary": return fmtUSD(v);
    case "employment_rate": return `${v}%`;
    case "stem_designation": return v.designated ? "Designated" : "Not designated";
    case "sponsorship": return `${v.employer}: ${v.statement}`;
    default: return typeof v === "object" ? JSON.stringify(v) : String(v);
  }
}
const factOf = (rec, n) => (rec.facts || []).find(f => f.fact === n);
function biggestUncertainty(rec) {
  if (rec.affordability === "unknown") return ["Total cost", "Cost of attendance isn't published, so budget fit is unknown."];
  if (rec.affordability === "over_budget") return ["Budget", "Published cost of attendance is above your budget."];
  if (rec.sponsorship_status === "unknown") return ["Visa sponsorship", "No employer-specific sponsorship evidence exists for this program."];
  return ["Outcomes", "Employment figures use the school's own definition."];
}
function sources(res, ids) {
  return ids.map(id => {
    const e = res.evidence[id];
    if (!e || e.missing) return el("div", { class: "src", text: `Evidence ${id} could not be resolved.` });
    return el("div", { class: "src" },
      el("div", { class: "spread" }, el("b", { text: `${SCHOOL[e.program_id] ? SCHOOL[e.program_id] + " · " : ""}${e.source_title}` }),
        el("span", { class: `tag ${e.rechecked ? "tag-teal" : ""}`, text: e.rechecked ? "Independently re-checked" : "Collected, not re-checked" })),
      el("blockquote", { text: `“${e.excerpt}”` }),
      el("div", { class: "xs muted" }, extLink(e.source_url, "Official page"), ` · ${e.source_label} · accessed ${e.checked_on || "unknown"} · data period ${e.data_period || "not stated"}`,
        e.excerpt_is_paraphrase ? " · paraphrased, not a verbatim quote" : "", e.freshness?.warning && !/not stated/i.test(e.freshness.warning) ? ` · ${e.freshness.warning}` : ""));
  });
}
async function renderResults(which, sub) {
  let res = S.result;
  if (which === "demo") {
    try { res = await api("/api/demo"); } catch (err) { put($main, el("div", { class: "wrap" }, note("bad", "Could not load the sample analysis.", err.message))); return; }
  } else if (!res || !res.report) {
    put($main, el("div", { class: "wrap empty" }, el("h2", { text: "No results in this session" }),
      el("p", { text: "Live results are kept in memory only." }), el("a", { class: "btn btn-primary", href: "#/results/demo", text: "See the sample analysis" })));
    return;
  }
  const view = { programs: "shortlist", strategy: "plan", skeptic: "evidence", trace: "evidence" }[sub] || (["plan", "evidence"].includes(sub) ? sub : "shortlist");
  const r = res.report, p = res.profile || {}, demo = res.mode === "saved_demo";
  const wrap = el("div", { class: "wrap" });
  const budget = p.budget_usd ? `${fmtUSD(p.budget_usd)} ${p.budget_period === "total_program" ? "for the whole program" : "a year"}` : "no budget given";
  put(wrap, el("div", { class: "res-head" },
    el("div", { class: "kicker", text: demo ? "Sample analysis · fictional applicant" : "Your analysis" }),
    el("h1", { text: view === "plan" ? "Your roadmap" : view === "evidence" ? "Evidence & risks" : "Your shortlist" }),
    el("p", { class: "lead", text: `${[p.target_function, p.target_industry].filter(Boolean).join(" in ") || "Career goal not given"} · ${budget}${p.citizenship_country ? ` · from ${p.citizenship_country}` : ""}` }),
    demo ? el("p", { class: "small muted", text: `A real ${r.model} analysis saved on 23 October 2026. Viewing it makes no AI call.` }) : null,
    note("", "Reviewer and legacy view.", el("span", {}, "The dashboard is the main view of this analysis. ", el("a", { href: `#/dashboard/${which}`, text: "Open the dashboard" })))),
    el("nav", { class: "seg subnav", "aria-label": "Analysis sections" }, [["shortlist", "Shortlist"], ["plan", "Roadmap"], ["evidence", "Evidence & risks"]].map(([v, t]) =>
      el("a", { href: `#/results/${which}/${v}`, "aria-current": view === v ? "page" : null, text: t }))));
  const host = el("div"); put(wrap, host); put($main, wrap);
  ({ shortlist: viewShortlist, plan: viewPlan, evidence: viewEvidence })[view](host, res, which);
}
function viewShortlist(host, res, which) {
  const r = res.report;
  const nonComparable = (r.metric_comparability || []).some(m => !m.all_comparable);
  put(host, el("div", {}, r.status !== "completed" && r.status !== "completed_with_violations" ? note("bad", `This run ended with status ${r.status}.`, errText(r.error)) : null,
    (r.recommendations || []).map(rec => recCard(rec, res)),
    nonComparable ? el("div", { style: "margin-top:32px" }, more("Compare employment outcomes",
      el("p", { class: "small muted", text: "Schools define these numbers differently (who is counted, and when), so they're shown side by side but not ranked." }),
      el("div", { class: "tbl-wrap" }, el("table", { class: "tbl" },
        el("thead", {}, el("tr", {}, ["Program", "Employment rate", "Definition", "Median base salary"].map(h => el("th", { text: h })))),
        el("tbody", {}, r.recommendations.map(rec => { const er = factOf(rec, "employment_rate"), ms = factOf(rec, "median_base_salary");
          return el("tr", {}, el("td", { text: SCHOOL[rec.program_id] || rec.program_name }), el("td", { text: er ? `${factValue(er)}${er.period ? ` (${er.period})` : ""}` : "—" }),
            el("td", { style: "white-space:normal;min-width:260px", text: er?.definition || "—" }), el("td", { text: ms ? factValue(ms) : "—" })); })))))) : null,
    (r.excluded_programs || []).length ? more("Programs considered but not shortlisted", r.excluded_programs.map(x => { const [, t] = splitLabel(x.reason);
      return el("p", { class: "small" }, el("b", { text: `${SCHOOL[x.program_id] || x.program_id}: ` }), t); })) : null,
    el("p", { class: "small muted", style: "margin-top:32px" }, "Shown in the Pathway Matcher's order — not a ranking, and never an admission estimate. ",
      el("a", { href: `#/results/${which}/plan`, text: "See your roadmap →" }))));
}
function recCard(rec, res) {
  const [, why] = splitLabel(rec.fit_rationale);
  const coa = factOf(rec, "cost_of_attendance"), stem = factOf(rec, "stem_designation"), loc = factOf(rec, "location");
  const [uTitle, uText] = biggestUncertainty(rec);
  const budgetLine = { within_budget: "Within your budget", over_budget: "Over your budget", unknown: "Budget fit unknown" }[rec.affordability] || rec.affordability;
  const ids = [...new Set((rec.facts || []).flatMap(f => f.evidence_ids))];
  return el("article", { class: "rec" },
    el("div", { class: "top" },
      el("div", {}, el("h2", { text: rec.program_name }), el("div", { class: "small muted", text: loc?.status === "verified" ? factValue(loc) : "Location unknown" })),
      el("span", { class: `tag ${rec.career_fit === "strong" ? "tag-teal" : ""}`, text: `${rec.career_fit[0].toUpperCase()}${rec.career_fit.slice(1)} career fit` })),
    el("p", { class: "why" }, el("span", { class: "label", text: "Why it fits · inference  " }), el("br"), why),
    el("div", { class: "keyfacts" },
      el("div", {}, el("div", { class: "k", text: "Cost and budget" }), el("div", { class: "v", text: coa?.status === "verified" ? `${factValue(coa)} a year` : "Total cost not published" }),
        el("div", { class: "d", text: `${budgetLine}${coa?.period ? ` · ${coa.period}` : ""}` })),
      el("div", {}, el("div", { class: "k", text: "STEM designation" }), el("div", { class: "v", text: rec.stem_status === "verified_designated" ? "Verified" : rec.stem_status === "unknown" ? "Unknown" : "Not designated" }),
        el("div", { class: "d", text: rec.stem_status === "verified_designated" ? "Official source · not a visa guarantee" : "" })),
      el("div", {}, el("div", { class: "k", text: "Most important uncertainty" }), el("div", { class: "v", text: uTitle }), el("div", { class: "d", text: uText }))),
    more("Details & sources",
      el("h4", { text: "Tradeoffs" }), (rec.tradeoffs || []).map(t => { const [l, x] = splitLabel(t); return el("div", { class: "claim" }, l ? labelEl(textLabel(l)) : el("span"), el("span", { text: x })); }),
      el("h4", { style: "margin-top:24px", text: "What the Evidence Analyst found" }),
      (rec.analyst_claims || []).map(c => el("div", { class: "claim" }, labelEl(c.label), el("span", { text: c.text }))),
      el("h4", { style: "margin-top:24px", text: "Key facts" }),
      el("div", { class: "factlist" }, (rec.facts || []).map(f => el("div", {}, el("span", { class: "muted", text: `${FACT_LABEL[f.fact]}: ` }),
        el("span", { class: f.status === "verified" ? "" : "unk", text: f.status === "verified" ? `${factValue(f).slice(0, 120)}${f.period ? ` (${f.period})` : ""}` : "Unknown" })))),
      el("h4", { style: "margin-top:24px", text: `Sources (${ids.length})` }), sources(res, ids)));
}
function viewPlan(host, res) {
  const s = res.report.strategy;
  if (!s) { put(host, el("p", { class: "muted", text: "The Strategy Planner did not finish in this run." })); return; }
  const key = `ac-plan-${res.report.run_id}`; let done = {};
  try { done = JSON.parse(localStorage.getItem(key)) || {}; } catch { /* ignore */ }
  const next = s.weekly_plan.flatMap(w => w.actions.map(a => ({ a, w: w.week, p: w.priority }))).sort((x, y) => (x.p === "high" ? 0 : 1) - (y.p === "high" ? 0 : 1) || x.w - y.w).slice(0, 3);
  const recText = { take_gmat: "Take the GMAT", take_gre: "Take the GRE", either_gmat_or_gre: "Either GMAT or GRE", use_existing_score: "Use your existing score",
    retake_existing_test: "Retake your current test", undecided_need_info: "Decide after a diagnostic" }[s.test_guidance.recommendation] || s.test_guidance.recommendation;
  put(host, el("div", {},
    el("h2", { text: "Your next three moves" }),
    el("div", { class: "next3", style: "margin:24px 0 48px" }, next.map((x, i) => el("div", { class: "card" }, el("div", { class: "n", text: String(i + 1) }), el("p", { style: "margin:0", text: x.a }), el("div", { class: "xs muted", style: "margin-top:8px", text: `Week ${x.w}` })))),
    el("div", { class: "card-quiet" }, el("div", { class: "kicker", text: "GMAT / GRE" }), el("h3", { text: recText }), el("p", { class: "small", style: "margin:0", text: s.test_guidance.rationale })),
    el("section", { style: "margin-top:48px" }, el("h2", { text: "Your week-by-week plan" }), el("p", { class: "small muted", text: "Tick things off as you go — saved in this browser only." }),
      s.weekly_plan.map(w => el("div", { class: "week" }, el("div", { class: "wk", text: `Week ${w.week}` }),
        el("div", {}, w.actions.map((a, j) => { const id = `${w.week}-${j}`;
          const lab = el("label", { class: `check${done[id] ? " done" : ""}` }, el("input", { type: "checkbox", checked: done[id] ? true : null,
            onchange: e => { done[id] = e.target.checked; lab.classList.toggle("done", e.target.checked); localStorage.setItem(key, JSON.stringify(done)); } }), el("span", { text: a }));
          return lab; }))))),
    el("section", { style: "margin-top:48px" }, el("h2", { text: "The journey" }),
      el("div", { class: "phases", style: "margin-top:24px" }, s.roadmap.map(ph => el("div", { class: `phase${ph.human_checkpoint ? " human" : ""}` },
        el("h4", { text: ph.phase }), el("div", { class: "xs muted", text: `${ph.timing}${ph.human_checkpoint ? " · your decision" : ""}` }),
        el("ul", { class: "small", style: "padding-left:18px;margin:8px 0 0" }, ph.milestones.map(m => el("li", { text: m })))))),
      el("p", { class: "small muted", style: "margin-top:24px", text: "Amber phases need your own judgement. Confirm deadlines on official pages, and take immigration questions to the school's DSO or a qualified attorney." })),
    more("Gaps behind this plan", [...s.gaps].sort((a, b) => ["high", "medium", "low"].indexOf(a.severity) - ["high", "medium", "low"].indexOf(b.severity))
      .map(g => el("div", { class: "claim" }, el("span", { class: `label ${g.severity === "high" ? "label-unknown" : ""}`, text: `${g.severity} priority` }), el("div", {}, el("b", { text: g.gap }), el("div", { class: "muted", text: g.action })))))));
}
function viewEvidence(host, res) {
  const r = res.report, sk = r.skeptic, t = r.totals || {}, events = res.events || [];
  const risks = [];
  for (const rec of r.recommendations || []) for (const f of rec.facts || [])
    if (["cost_of_attendance", "sponsorship", "international_employment", "employment_rate"].includes(f.fact) && f.status !== "verified")
      risks.push(f.fact === "sponsorship" && rec.sponsorship_status === "employer_specific_evidence"
        ? `${SCHOOL[rec.program_id] || rec.program_name}: no school-level sponsorship statement (historical employer H-1B filings exist — not a guarantee)`
        : `${SCHOOL[rec.program_id] || rec.program_name}: ${FACT_LABEL[f.fact].toLowerCase()} unknown`);
  const allIds = [...new Set((r.recommendations || []).flatMap(rec => (rec.facts || []).flatMap(f => f.evidence_ids)))];
  const feed = el("ol", { class: "feed" }); events.forEach(e => put(feed, feedItem(e)));
  put(host, el("div", {}, 
    el("div", { class: "promise" },
      el("div", {}, el("h2", { text: "The Skeptic's review" }), sk ? el("p", { text: sk.overall_assessment }) : el("p", { class: "muted", text: "The Skeptic did not run." }),
        el("p", { class: "small muted", text: r.revision_performed ? `It requested one revision of the ${AGENT_NAME[r.revision_target]}, which was completed.` : "It did not request a revision." }),
        (sk?.findings || []).map(f => note(f.severity === "high" ? "bad" : "warn", `${f.severity[0].toUpperCase() + f.severity.slice(1)} · ${AGENT_NAME[f.target_agent]}.`, el("span", {}, f.issue, el("br"), el("span", { class: "muted", text: `Fix: ${f.required_fix}` }))))),
      el("div", {}, el("h2", { text: "What's still unknown" }), risks.length ? el("ul", { class: "ticks" }, risks.map(x => el("li", { text: x }))) : el("p", { class: "muted", text: "Nothing key is unknown." }),
        el("p", { class: "small muted", style: "margin-top:16px", text: "Unknown means the official pages we reached didn't publish it — not that the answer is no." }))),
    el("section", { class: "section", style: "padding-bottom:0" },
      more(`Automatic safeguards (${(r.grounding_violations || []).length})`,
        el("p", { class: "small muted", text: "Code checks that run after every agent: ids must exist, numbers must match evidence, statuses are recomputed, and risky wording is flagged." }),
        (r.grounding_violations || []).map(v => { const [label, detail] = safeguardText(v);
          return el("div", { class: "claim" }, el("span", { class: "label", text: label }), el("div", {}, el("div", { text: detail }), el("div", { class: "xs muted", text: `${AGENT_NAME[v.agent] || "Agent"} · ${v.action}` }))); }),
        res.mode === "saved_demo" ? el("p", { class: "xs muted", text: "Note: this saved run's one flag was a false positive — the analyst was correctly warning that STEM status doesn't guarantee immigration benefits. The rule was fixed afterwards." }) : null),
      more(`All citations (${allIds.length})`, sources(res, allIds)),
      more("Usage and cost",
        el("p", { class: "small", text: `${fmtInt(t.model_requests)} model requests · ${fmtInt(t.input_tokens)} input tokens (${fmtInt(t.cached_input_tokens)} cached) · ${fmtInt(t.output_tokens)} output tokens (${fmtInt(t.reasoning_tokens_within_output)} reasoning) · ${fmtInt(t.tool_calls)} lookups · ${t.wall_seconds ?? "—"} s · cost unknown (no published gpt-6-luna price).` }),
        el("div", { class: "tbl-wrap" }, el("table", { class: "tbl" }, el("thead", {}, el("tr", {}, ["Agent", "Requests", "Input", "Cached", "Output", "Reasoning", "Model time"].map(h => el("th", { text: h })))),
          el("tbody", {}, (r.usage_by_agent || []).map(u => el("tr", {}, [AGENT_NAME[u.agent], u.calls, fmtInt(u.input_tokens), fmtInt(u.cached_input_tokens), fmtInt(u.output_tokens), fmtInt(u.reasoning_tokens), `${u.elapsed_seconds}s`].map(x => el("td", { text: x }))))))),
        res.mode === "saved_demo" ? el("p", { class: "xs muted", text: "Measurement note: requests 1–9 of this saved run returned token counts identical to an earlier run, 8 in under a second — likely served from Portkey's response cache. Requests 10–16 were fresh." }) : null,
        res.verification ? el("p", { class: "xs muted", text: `Post-run audit: ${res.verification.ok ? "passed" : "problems found"} — every evidence id checked against the store; no unsupported numbers.` }) : null),
      more(`Technical run details (${events.length} events)`, el("p", { class: "xs muted", text: "For reviewers: the raw agent trace — lookups with their internal tool names and arguments, handoffs, checks and token counts. Prompts and model reasoning are never stored or shown." }), feed))));
}
/* Grounding rules and details are internal identifiers; show people a plain label and drop schema paths such as
   "unsupported_claims_flagged[4]:" from the start of the detail. */
const SAFEGUARD_LABEL = { guarantee: "Unsupported claims reviewed", sponsorship_guarantee: "Unsupported claims reviewed", unknown_evidence_id: "Citation not found",
  unknown_program_id: "Unknown program", program_not_in_shortlist: "Program not on the shortlist", incomparable_metrics: "Figures not comparable",
  risky_or_dated_action: "Risky or dated advice", risky_or_dated_milestone: "Risky or dated milestone", revision_limit: "Revision limit reached" };
function safeguardText(v) {
  const label = SAFEGUARD_LABEL[v.rule] || (v.rule || "safeguard").replace(/_/g, " ").replace(/^./, c => c.toUpperCase());
  const detail = String(v.detail || "").replace(/^[a-z][a-z0-9_]*(\[\d+\])?(\.[a-z][a-z0-9_]*(\[\d+\])?)*:\s*/, "");
  return [label, detail];
}

/* ---------------- Career Intelligence dashboard (Step 10) ----------------
   Every value comes from /api/dashboard/:id — the saved/live run plus the evidence store. Calculations are done server-side in code. */
const DFACT = { location: "Location", test_policy: "Test policy", tuition: "Tuition", cost_of_attendance: "Cost of attendance", stem_designation: "STEM designation",
  employment_rate: "Employment rate", median_base_salary: "Median base salary", international_employment: "International outcomes", sponsorship: "Employer sponsorship" };
const PERIOD_TEXT = p => (p === "total_program" ? "for the whole program" : "per academic year");
function srcLinks(dres, ids) {
  const seen = new Set();
  const links = (ids || []).map(id => dres.evidence[id]).filter(e => e && !e.missing && e.source_url && !seen.has(e.source_url) && seen.add(e.source_url));
  if (!links.length) return el("span", { class: "xs muted", text: "No source on file" });
  return el("span", { class: "dsrc" }, links.map((e, i) => [i ? " · " : "", extLink(e.source_url, `Source: ${e.source_title}`)]));
}
async function renderDashboard(runId) {
  let dres;
  try { dres = await api(`/api/dashboard/${encodeURIComponent(runId)}`); }
  catch (err) {
    put($main, el("div", { class: "wrap empty" }, el("h2", { text: "This dashboard isn't available" }), el("p", { class: "muted", text: err.message }),
      el("a", { class: "btn btn-primary", href: "#/dashboard/demo", text: "Open the sample dashboard" }))); return;
  }
  const d = dres.dashboard, p = dres.profile || {}, demo = dres.mode === "saved_demo";
  const res = { evidence: dres.evidence };
  let sel = d.programs[0]?.program_id;
  const wrap = el("div", { class: "wrap dash dash2" });
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const jump = id => () => document.getElementById(id)?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  const pw = d.pathway, timing = planTiming(d.programs), td = d.test_decision;
  const sevRank = { high: 0, medium: 1, low: 2 };
  const gaps = [...(pw.gaps || [])].sort((x, y) => (sevRank[x.severity] ?? 3) - (sevRank[y.severity] ?? 3));
  const name = pg => SCHOOL[pg.program_id] || pg.program_name;
  const target = pw.target.roles[0] || pw.target.function || "your target role";
  const strong = d.programs.filter(pg => pg.fit?.career_fit === "strong").map(name);
  const wk = d.workspace.weekly, byId = Object.fromEntries(d.workspace.tasks.map(t => [t.id, t]));
  let doneIds = {};
  try { doneIds = JSON.parse(localStorage.getItem(`ac-workspace-${d.run.run_id || runId}`)) || {}; } catch { doneIds = {}; }
  const firstAction = (wk?.weeks || []).flatMap(x => x.priority).find(id => !doneIds[id]);
  const undecided = td?.state === "undecided_no_diagnostic";

  /* 1. top summary: who, where to, one sentence, three decisions, one primary action */
  put(wrap, el("header", { class: "ds-top" },
    el("div", { class: "kicker", text: demo ? "Sample analysis · fictional applicant" : "Your analysis" }),
    el("h1", { text: demo ? "Sample analysis" : "Your analysis" }),
    el("p", { class: "ds-who" }, el("span", { text: [pw.background.role, pw.background.industry, pw.background.years != null ? `${pw.background.years} years` : null].filter(Boolean).join(" · ") || "Background not given" }),
      el("span", { class: "ds-arrow", "aria-hidden": "true", text: " → " }), el("b", { text: target })),
    el("p", { class: "ds-rec", text: `Research the ${d.programs.length} programs shortlisted for a ${target} path${strong.length ? ` — ${strong.join(" and ")} ${strong.length > 1 ? "fit" : "fits"} your career goal best` : ""}${undecided ? ", and take timed diagnostics before choosing between the GRE and GMAT" : ""}.` }),
    el("div", { class: "ds-decisions" },
      el("div", { class: "ds-dec" }, el("span", { class: "ds-k", text: "School shortlist" }), el("b", { text: `${d.programs.length} programs` }),
        el("span", { class: "ds-v", text: strong.length ? `Strongest fit: ${strong.join(", ")}` : d.programs.map(name).join(", ") })),
      el("div", { class: "ds-dec" }, el("span", { class: "ds-k", text: "GRE or GMAT" }), el("b", { text: undecided ? "Undecided" : (PLANNER_TEST_TEXT[td?.planner_recommendation] || "See the test section") }),
        el("span", { class: "ds-v", text: undecided ? "No diagnostic scores yet — take one timed practice test of each" : "Based on your profile" })),
      el("div", { class: "ds-dec" }, el("span", { class: "ds-k", text: "Next action this week" }),
        firstAction ? [el("b", { text: byId[firstAction].text }), el("span", { class: "ds-v", text: `About ${wk.actions[firstAction].minutes} minutes · planning estimate` })]
          : el("b", { text: "All planned actions are marked done" }))),
    el("div", { class: "ds-cta" },
      el("button", { type: "button", class: "btn btn-primary btn-lg", onclick: jump("d-plan") }, "Start this week's plan ", arrow()),
      el("button", { type: "button", class: "btn btn-quiet", onclick: jump("d-short"), text: "See the shortlist" })),
    demo ? el("p", { class: "ds-note", text: "A saved analysis for a fictional applicant. Viewing it makes no AI call." }) : null));

  /* 2. shortlist: four compact cards; "View evidence" opens that school's full source-backed details */
  const drawer = el("div", { class: "ds-drawer", hidden: true });
  let open = null;
  const openEvidence = pg => {
    if (open === pg.program_id) { open = null; drawer.hidden = true; clear(drawer); drawCards(); return; }
    open = pg.program_id; sel = pg.program_id; drawPrograms();
    const f = el("div"), c = el("div"), i = el("div");
    drawFit(f, pg, res); drawCost(c, pg, dres); drawIntl(i, pg, dres);
    put(clear(drawer), el("div", { class: "spread" }, el("h3", { text: `Evidence for ${name(pg)}` }),
      el("button", { type: "button", class: "btn btn-quiet", onclick: () => openEvidence(pg), text: "Close" })),
      el("h4", { text: "Program fit" }), f, el("h4", { text: "Affordability" }), c, pg.feasibility ? [el("h4", { text: "International feasibility" }), i] : null);
    drawer.hidden = false; drawCards(); drawer.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };
  const cards = el("div", { class: "ds-cards" });
  const drawCards = () => put(clear(cards), d.programs.map(pg => shortlistCard(pg, open === pg.program_id, () => openEvidence(pg))));
  drawCards();
  put(wrap, el("section", { class: "ds-sec", id: "d-short", "aria-labelledby": "h-short" },
    el("h2", { id: "h-short", text: "Shortlist" }),
    el("p", { class: "ds-lead", text: "Ordered by the Pathway Matcher, not ranked. No match scores or admission odds." }), cards, drawer));

  /* 3. test decision: compact card; policy evidence behind an expander */
  if (td) put(wrap, el("section", { class: "ds-sec", id: "d-test", "aria-labelledby": "h-test" },
    el("h2", { id: "h-test", text: "GRE or GMAT" }),
    el("div", { class: "ds-card" },
      el("div", { class: "ds-row" }, el("b", { class: "ds-big", text: undecided ? "Undecided — and that's the honest answer" : (PLANNER_TEST_TEXT[td.planner_recommendation] || "See the Strategy Planner's note") }),
        undecided ? null : badge("ai")),
      el("p", { text: undecided ? "There are no timed results to compare yet, so neither test is recommended. Neither is picked because it's more common." : (td.planner_rationale || "") }),
      undecided ? el("p", { class: "ds-next" }, el("b", { text: "Next: " }), "take one full-length, timed official practice test of each — either first. About 2½–3 hours each, including a short review (planning estimate).") : null,
      more("View each school's test policy (official sources)", testPolicyList(d)))));

  /* 4. profile gaps: top three; the rest behind "View all gaps" */
  put(wrap, el("section", { class: "ds-sec", id: "d-gaps", "aria-labelledby": "h-gaps" },
    el("h2", { id: "h-gaps", text: "Profile gaps" }),
    el("p", { class: "ds-lead", text: "Based on your profile. The three most important first." }),
    gaps.length ? el("ol", { class: "ds-gaps" }, gaps.slice(0, 3).map(gapItem)) : el("p", { text: "No gaps were identified." }),
    gaps.length > 3 ? more(`View all gaps (${gaps.length})`, el("ol", { class: "ds-gaps", start: "4" }, gaps.slice(3).map(gapItem))) : null));

  /* 5. weekly plan: the current week only (3–5 actions); the full plan lives in the collapsed panel below */
  const weekHost = el("div"), workHost = el("div");
  const fullPlan = panel("Full plan and deadlines", "d-work", workHost);
  put(wrap, el("section", { class: "ds-sec", id: "d-plan", "aria-labelledby": "h-plan" },
    el("h2", { id: "h-plan", text: "This week's plan" }), timingNote(timing), weekHost,
    el("button", { type: "button", class: "btn btn-quiet", onclick: () => { fullPlan.open = true; workHost.querySelector("details.dplan")?.setAttribute("open", ""); fullPlan.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }); },
      text: `View full ${wk?.weeks?.length ? `${wk.weeks.length}-week ` : ""}plan` })));

  /* 6. detailed evidence: every long section, collapsed by default */
  const picker = el("div", { class: "dpick", role: "group", "aria-label": "Show details for" });
  const fitHost = el("div"), costHost = el("div"), intlHost = el("div");
  const drawPrograms = () => {
    clear(picker);
    setChatContext({ ...(demo ? { run: "demo" } : {}), program_id: sel });
    d.programs.forEach(pg => put(picker, el("button", { type: "button", class: "dprog", "aria-pressed": pg.program_id === sel ? "true" : "false",
      onclick: () => { sel = pg.program_id; drawPrograms(); } }, el("b", { text: name(pg) }), el("span", { class: "xs muted", text: `${pg.fit.career_fit} career fit` }))));
    const pg = d.programs.find(x => x.program_id === sel);
    drawFit(fitHost, pg, res); drawCost(costHost, pg, dres); drawIntl(intlHost, pg, dres);
  };
  put(wrap, el("section", { class: "ds-sec ds-details", id: "d-details", "aria-labelledby": "h-details" },
    el("h2", { id: "h-details", text: "Detailed evidence" }),
    el("p", { class: "ds-lead", text: "Everything behind the summary, with sources, verification status, dates checked, unknowns and tradeoffs." }),
    el("div", { class: "ds-pick" }, el("span", { class: "ds-k", text: "School shown in the panels" }), picker),
    panel("Career pathway details", "d-path", careerPathwayBlock(d)),
    td ? panel("GRE or GMAT evidence", "d-test-ev", drawTestDecision(d, p, timing)) : null,
    panel("Program fit", "d-fit", fitHost),
    panel("Affordability", "d-cost", costHost),
    panel("International feasibility", "d-intl", intlHost),
    fullPlan),
    el("section", { class: "ds-sec ds-review", "aria-label": "Reviewer details" },
      panel("Reviewer details", "d-review", el("div", {},
        el("p", {}, `Analysis status: ${RUN_STATUS_TEXT[d.run.status] || "not recorded"}. Model: ${d.run.model}. ${demo ? "Saved on 23 October 2026 and combined with today's evidence store." : ""}`),
        el("p", {}, el("a", { href: `#/results/${runId}/evidence`, text: "Skeptic review, citations, usage and technical trace" }),
          " · Legacy views: ", el("a", { href: `#/results/${runId}/shortlist`, text: "shortlist" }), " · ", el("a", { href: `#/results/${runId}/plan`, text: "roadmap" })),
        runDetailsPanel(runId), safetyTestPanel()))));
  put($main, wrap);
  drawPrograms();
  let remote = null;
  if (S.user) { try { remote = (await api(`/api/account/progress/${encodeURIComponent(d.run.run_id || runId)}`)).done; } catch { remote = null; } }
  drawWorkspace(workHost, d, dres, runId, id => { sel = id; drawPrograms(); jump("d-details")(); }, remote, weekHost, timing);
}
/* ---- summary-page building blocks ---- */
/* Applicant-facing labels in plain language; the technical statuses stay in the evidence panels. */
const BADGE = { verified: ["ok", "Official source"], estimated: ["warn", "Planning estimate"], unknown: ["", "Needs confirmation"], passed: ["", "Passed"], upcoming: ["ok", "Upcoming"], ai: ["ai", "Based on your profile"] };
function badge(kind, text) { const [cls, def] = BADGE[kind] || ["", kind]; return el("span", { class: `dtag ds-badge ${cls}`, text: text || def }); }
function panel(title, id, content) {
  return el("details", { class: "ds-panel", id }, el("summary", {}, el("span", { text: title })), el("div", { class: "ds-panel-body" }, content));
}
function gapItem(g) {
  return el("li", {}, el("b", { text: g.gap }), el("p", { text: g.action }));
}
function shortlistCard(pg, isOpen, onEvidence) {
  const a = pg.affordability || {}, tp = pg.test_policy || {}, dl = deadlineRounds(pg.deadlines);
  const cost = a.comparable ? [badge("verified"), ` ${a.gap >= 0 ? `Within budget by ${fmtUSD(a.gap)}` : `${fmtUSD(-a.gap)} over budget`} a year`]
    : a.estimate ? [badge("estimated"), ` About ${fmtUSD(a.estimate.value)} a year (${a.estimate.publisher})`] : [badge("unknown"), " Total cost not published"];
  const test = tp.status === "verified" ? [badge("verified"), ` ${String(tp.summary).split(";")[0]}`] : [badge("unknown"), " Not established"];
  const next = dl.next ? [badge("upcoming"), ` ${dl.next.name} · ${fmtDate(dl.next.date)}`] : dl.status === "unverified" ? [badge("unknown"), " Not verified"] : [badge("passed", "All passed"), " No upcoming round verified"];
  const trade = (pg.fit?.tradeoffs || []).map(t => splitLabel(t)[1]).find(Boolean);
  return el("article", { class: `ds-school${isOpen ? " open" : ""}` },
    el("div", { class: "ds-school-head" }, el("h3", { text: SCHOOL[pg.program_id] || pg.program_name }),
      el("span", { class: `ds-fit ${pg.fit?.career_fit || ""}`, text: pg.fit?.career_fit ? `${pg.fit.career_fit} career fit` : "career fit not rated" })),
    el("dl", {},
      el("div", {}, el("dt", { text: "Cost" }), el("dd", {}, cost)),
      el("div", {}, el("dt", { text: "Test policy" }), el("dd", {}, test)),
      el("div", {}, el("dt", { text: "Next deadline" }), el("dd", {}, next)),
      trade ? el("div", {}, el("dt", { text: "Tradeoff" }), el("dd", { text: trade })) : null),
    el("button", { type: "button", class: "btn btn-secondary ds-ev", "aria-expanded": isOpen ? "true" : "false", onclick: onEvidence, text: isOpen ? "Hide evidence" : "View evidence" }));
}
function careerPathwayBlock(d) {
  const pw = d.pathway;
  return el("div", {},
    el("div", { class: "dpath" },
      el("div", { class: "dnode from" }, el("div", { class: "xs k", text: "Where you are" }), el("b", { text: pw.background.role || "Not given" }),
        el("div", { class: "small muted", text: [pw.background.industry, pw.background.years != null ? `${pw.background.years} years` : null].filter(Boolean).join(" · ") })),
      el("div", { class: "dlink", "aria-hidden": "true", text: "→" }),
      el("div", { class: "dnode mid" }, el("div", { class: "xs k", text: "Education step" }), el("b", { text: "MBA" }),
        el("div", { class: "small muted", text: `${d.programs.length} programs shortlisted by career fit` })),
      el("div", { class: "dlink", "aria-hidden": "true", text: "→" }),
      el("div", { class: "dnode to" }, el("div", { class: "xs k", text: "Where you want to go" }), el("b", { text: pw.target.roles[0] || pw.target.function || "Not given" }),
        el("div", { class: "small muted", text: pw.target.industry || "" }))),
    el("h4", { text: "Strengths" }), el("p", {}, badge("verified", "From your profile")),
    el("ul", { class: "dlist" }, pw.profile_facts.map(f => el("li", {}, el("span", { class: "muted", text: `${f.label}: ` }), f.value))),
    el("h4", { text: "All gaps" }), el("p", {}, badge("ai", "AI-inferred · Strategy Planner")),
    el("ul", { class: "dlist" }, pw.gaps.map(g => el("li", {}, el("span", { class: `sev ${g.severity}`, text: g.severity }), " ", el("b", { text: g.gap }), el("div", { class: "small muted", text: g.action })))));
}
/* GRE vs GMAT. The state comes from code (no diagnostic score -> undecided); nothing here predicts scores, ranks the
   tests by popularity or estimates admission odds. School policies are the verified official facts with their excerpts. */
const TEST_STATUS_TEXT = { not_started: "haven't started test preparation", preparing: "are preparing for a test", unknown: "haven't said where you are with testing",
  gmat_taken: "have taken the GMAT", gmat_focus_taken: "have taken the GMAT Focus Edition", gre_taken: "have taken the GRE", ea_taken: "have taken the Executive Assessment" };
const PLANNER_TEST_TEXT = { take_gmat: "Take the GMAT", take_gre: "Take the GRE", either_gmat_or_gre: "Either test works", use_existing_score: "Use your existing score",
  retake_existing_test: "Retake your current test", undecided_need_info: "Decide after a diagnostic" };
function testPolicyList(d) {
  return el("ul", { class: "dlist dpolicies" }, d.programs.map(pg => { const tp = pg.test_policy || {};
    const ev = (tp.evidence || []).find(e => e.source_url) || {};
    return el("li", {}, el("b", { text: SCHOOL[pg.program_id] || pg.program_name }),
      tp.status === "verified"
        ? [el("div", { class: "small", text: tp.summary }),
           ev.excerpt ? el("blockquote", { class: "dquote small", text: `${ev.excerpt_is_paraphrase ? "Paraphrase" : "Official page"}: “${ev.excerpt}”` }) : null,
           el("div", { class: "xs muted" }, ev.checked_on ? `Checked ${fmtDate(ev.checked_on)} · ` : "", ev.source_url ? extLink(ev.source_url, "Confirm on the official admissions page") : "No official link on file")]
        : el("div", { class: "small unk", text: "Test policy not established from official pages — check the school's admissions page before choosing a test." })); }));
}
function drawTestDecision(d, p, timing) {
  const td = d.test_decision, undecided = td.state === "undecided_no_diagnostic";
  const policies = testPolicyList(d);
  const evidence = el("div", { class: "dcard" }, el("h3", { text: "Each school's current test policy" }), el("span", { class: "dtag fact", text: "Official sources" }), policies,
    el("p", { class: "xs muted", text: "Policies change between cycles. Confirm on each official admissions page before you register for a test." }));
  if (!undecided) {
    return el("div", {}, el("div", { class: "dcard" },
      el("h3", { text: PLANNER_TEST_TEXT[td.planner_recommendation] || "See the Strategy Planner's note" }), el("span", { class: "dtag ai", text: "AI-inferred · Strategy Planner" }),
      td.planner_rationale ? el("p", { class: "small", text: td.planner_rationale }) : null), evidence);
  }
  const next = timing?.earliest;
  return el("div", {},
    el("div", { class: "dcols" },
      el("div", { class: "dcard" }, el("h3", { text: "Undecided — and that's the honest answer" }), el("span", { class: "dtag warn", text: "No diagnostic scores yet" }),
        el("p", { class: "small", text: `Your profile says you ${TEST_STATUS_TEXT[td.test_status] || "haven't reported a test result"} and lists no diagnostic score. With no timed results to compare, there's no basis for choosing one test over the other, so AdmitCompass doesn't pick one. Neither test is recommended just because more people take it.` }),
        el("p", { class: "xs muted", text: "No score predictions or admission odds are shown: there's no diagnostic data to base them on." }),
        td.planner_rationale ? more("Strategy Planner's note (AI-inferred)", el("p", { class: "small", text: td.planner_rationale })) : null),
      el("div", { class: "dcard" }, el("h3", { text: "Two-test diagnostic plan" }),
        el("ol", { class: "dlist dsteps" },
          el("li", {}, el("b", { text: "Take one full-length, timed official GMAT Focus Edition practice test" }), el("div", { class: "small muted" }, "Official practice materials: ", extLink("https://www.mba.com/", "mba.com"))),
          el("li", {}, el("b", { text: "Within about a week, take one full-length, timed official GRE practice test" }), el("div", { class: "small muted" }, "Same conditions: quiet room, timed, no breaks beyond the official ones. Official practice materials: ", extLink("https://www.ets.org/gre.html", "ets.org"))),
          el("li", {}, el("b", { text: "Compare the two with the decision rule below, then pick one test" }))))),
    el("div", { class: "dcard dnextact" }, el("span", { class: "dtag ai", text: "Next action" }),
      el("p", {}, el("b", { text: "Take the first full-length timed practice test this week — either test first." }),
        el("br"), el("span", { class: "small muted", text: "Estimated time: about 2½–3 hours, including setup and a short review of the results (planning estimate, not an official test length)." }))),
    el("div", { class: "dcard" }, el("h3", { text: "Decision rule" }),
      el("table", { class: "tbl drule" }, el("tbody", {}, [
        ["Timed performance", "Compare each result as a percentile, not a raw score — the two tests use different scales."],
        ["Preparation burden", "Which test's weaker sections would take fewer study hours to bring up to your goal?"],
        ["Target-school acceptance", "The test must be accepted by every program you apply to — see each school's official policy below."],
        ["Scheduling logistics", `Test dates and official score reports must fit before your target round.${next ? ` Earliest upcoming verified deadline on your shortlist: ${next.school} ${next.name}, ${fmtDate(next.date)}.` : " No upcoming deadline is verified for your shortlist yet."}`]]
        .map(([k, v]) => el("tr", {}, el("th", { scope: "row", text: k }), el("td", { text: v })))))),
    evidence);
}
/* ---------- developer / report view: run details + safety test mode (collapsed for ordinary users) ---------- */
function downloadJSON(name, data) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = el("a", { href: url, download: name }); document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function runDetailsPanel(runId) {
  const body = el("div", { class: "inner" }, el("p", { class: "small muted", text: "Loading…" }));
  const d = el("details", { class: "more drun", ontoggle: async e => {
    if (!e.target.open || body.dataset.loaded) return;
    body.dataset.loaded = "1";
    try {
      const rec = await api(runId === "demo" ? "/api/demo/record" : `/api/runs/${encodeURIComponent(runId)}/record`);
      put(clear(body),
        el("dl", { class: "drun-sum" }, rec.summary.map(x => el("div", {}, el("dt", { text: x.label }), el("dd", { text: x.value })))),
        el("div", { class: "dactions" },
          el("button", { type: "button", class: "btn btn-secondary", onclick: () => downloadJSON(`admitcompass-run-${rec.run_id || runId}.json`, rec), text: "Download JSON record" })),
        el("p", { class: "xs muted", text: rec.privacy }));
    } catch (err) { put(clear(body), el("p", { class: "small", text: `Run details aren't available: ${err.message}` })); }
  } }, el("summary", { text: "Run details (developer / report view)" }), body);
  return d;
}
function safetyTestPanel() {
  const body = el("div", { class: "inner" });
  const run = async b => {
    b.disabled = true; b.textContent = "Running…";
    try {
      const r = await api("/api/safety/demo");
      put(clear(body), el("p", { class: "small" }, el("b", { text: `${r.stopped} of ${r.total} defenses stopped the unsafe input.` }), " No AI call was made; each check runs the app's own code."),
        el("div", { class: "tbl-wrap" }, el("table", { class: "tbl devtbl" },
          el("thead", {}, el("tr", {}, ["Defense", "Unsafe input", "Result", "What the user sees"].map(h => el("th", { scope: "col", text: h })))),
          el("tbody", {}, r.scenarios.map(x => el("tr", {},
            el("td", {}, el("b", { text: x.defense }), el("div", { class: "xs muted", text: x.mechanism })),
            el("td", { class: "small", text: x.input }),
            el("td", {}, el("span", { class: `dtag ${x.stopped ? "ok" : "warn"}`, text: x.stopped ? "Stopped" : "Not stopped" }), el("div", { class: "xs", text: x.outcome })),
            el("td", { class: "small", text: x.shown_to_user })))))));
    } catch (err) { put(clear(body), el("p", { class: "small", text: `The safety checks couldn't run: ${err.message}` })); }
  };
  put(body, el("p", { class: "small muted", text: "Runs five defenses on fixed unsafe inputs: prompt injection in a source, an admissions-odds request, a personal immigration question, stale or missing data, and an answer that contradicts verified evidence." }),
    el("button", { type: "button", class: "btn btn-secondary", onclick: e => run(e.currentTarget), text: "Run the safety checks" }));
  return el("details", { class: "more drun" }, el("summary", { text: "Safety test mode" }), body);
}
const RUN_STATUS_TEXT = {
  completed: "completed",
  completed_with_violations: "completed — automatic safeguards removed or flagged some AI claims (see the reviewer details at the bottom)",
  stopped_budget: "stopped at the request budget; results may be partial",
  failed: "stopped safely before finishing; nothing was guessed to fill gaps",
};

/* Deadline status, computed against the viewer's date (window.AC_TODAY overrides it, for testing). */
const todayISO = () => window.AC_TODAY || (d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`)(new Date());
const isISODate = v => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v);
const fmtDate = iso => new Date(`${iso}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
function deadlineRounds(dl, today = todayISO()) {
  if (!dl || dl.status !== "verified") return { status: "unverified", rounds: [], passed: [], next: null };
  const rounds = (Array.isArray(dl.rounds) ? dl.rounds : [dl.rounds]).filter(Boolean).map(r => {
    const date = r && typeof r === "object" ? r.deadline : null;
    const name = r && typeof r === "object" ? (r.round || "Round") : String(r);
    return { name, date, status: isISODate(date) ? (date < today ? "passed" : "upcoming") : "unverified" };
  });
  const upcoming = rounds.filter(r => r.status === "upcoming").sort((a, b) => a.date.localeCompare(b.date));
  return { status: "verified", rounds, passed: rounds.filter(r => r.status === "passed"), next: upcoming[0] || null };
}
function planTiming(programs) {
  const info = programs.map(pg => ({ school: SCHOOL[pg.program_id] || pg.program_name, ...deadlineRounds(pg.deadlines) }));
  const nexts = info.filter(x => x.next).map(x => ({ school: x.school, ...x.next })).sort((a, b) => a.date.localeCompare(b.date));
  return { passedAt: info.filter(x => x.passed.length).map(x => x.school), earliest: nexts[0] || null, unverifiedAt: info.filter(x => x.status === "unverified" || (!x.next && !x.passed.length)).map(x => x.school) };
}
function timingNote(t) {
  const parts = [];
  if (t.passedAt.length) parts.push(`Earlier deadlines have passed at ${t.passedAt.join(", ")}.`);
  parts.push(t.earliest ? `Plan weeks count from the day you start; aim for the next open round — the earliest is ${t.earliest.school} ${t.earliest.name}, ${fmtDate(t.earliest.date)}.`
    : "No upcoming deadline is verified for the shortlist — confirm the next cycle on each official admissions page before planning.");
  if (t.unverifiedAt.length) parts.push(`Deadlines unverified for ${t.unverifiedAt.join(", ")}.`);
  return el("p", { class: `small dtiming${t.passedAt.length ? " late" : ""}`, text: parts.join(" ") });
}
const DL_TAG = { passed: ["", "Passed"], upcoming: ["ok", "Upcoming"], unverified: ["warn", "Unverified"] };
function drawFit(host, pg, res) {
  const f = pg.fit;
  clear(host);
  put(host, el("div", { class: "dcard" },
    el("div", { class: "spread" }, el("h3", { text: pg.program_name }), el("span", { class: `dtag ${f.career_fit === "strong" ? "ok" : ""}`, text: `${f.career_fit} career fit` })),
    el("p", {}, el("span", { class: "dtag ai", text: "Why it fits · AI inference" }), el("br"), f.why),
    el("div", { class: "dcols" },
      el("div", {}, el("h4", { text: `Supported by evidence (${f.supported.length})` }),
        f.supported.length ? el("ul", { class: "dlist" }, f.supported.map(c => el("li", {}, c.text, el("div", {}, srcLinks(res, c.evidence_ids))))) : el("p", { class: "small muted", text: "No evidence-linked claims." })),
      el("div", {}, el("h4", { text: "Unknowns" }),
        el("ul", { class: "dlist" }, f.unknown_facts.map(x => el("li", { class: "unk", text: `${DFACT[x] || x}: not established from official sources` })),
          f.unknown_claims.map(c => el("li", { class: "unk", text: c.text }))))),
    f.tradeoffs.length ? more("Tradeoffs (AI inference)", el("ul", { class: "dlist" }, f.tradeoffs.map(t => el("li", { text: splitLabel(t)[1] })))) : null,
    f.reasoning.length ? more(`Analyst reasoning (${f.reasoning.length})`, f.reasoning.map(c => el("div", { class: "claim" }, labelEl(c.label), el("span", { text: c.text })))) : null,
    evidenceTable(pg.evidence_rows),
    more("Source excerpts", sources(res, [...new Set(f.supported.flatMap(c => c.evidence_ids))]))));
}
/* One row per important claim: status, source, date checked, data period and a short tradeoff — all built in code. */
const EV_STATUS = { verified: ["ok", "Verified"], "source-backed paraphrase": ["fact", "Source-backed paraphrase"], estimated: ["warn", "Estimated"], unknown: ["", "Unknown"] };
function evidenceTable(rows) {
  if (!rows?.length) return null;
  return el("div", { class: "dev" }, el("h4", { text: "Evidence behind this recommendation" }),
    el("div", { class: "tbl-wrap" }, el("table", { class: "tbl devtbl" },
      el("thead", {}, el("tr", {}, ["Claim", "Status", "Source", "Checked", "Data period", "Tradeoff"].map(h => el("th", { scope: "col", text: h })))),
      el("tbody", {}, rows.map(r => el("tr", { class: r.status === "unknown" ? "unk" : "" },
        el("td", {}, r.claim, r.freshness_warning ? el("div", { class: "xs dwarn", text: r.freshness_warning }) : null),
        el("td", {}, el("span", { class: `dtag ${(EV_STATUS[r.status] || ["", r.status])[0]}`, text: (EV_STATUS[r.status] || ["", r.status])[1] })),
        el("td", {}, r.source_url ? extLink(r.source_url, r.source_title || r.publisher || "Source") : el("span", { class: "muted", text: "—" })),
        el("td", { text: r.checked_on ? fmtDate(r.checked_on) : "—" }),
        el("td", { text: r.data_period || "not stated" }),
        el("td", { class: "small", text: r.tradeoff })))))),
    el("p", { class: "xs muted", text: "Verified = quoted from an official page. Paraphrase = the official page says it in other words. Estimated = a third party's figure, not the school's. Unknown = not on the official pages checked; nothing is guessed." }));
}
function drawCost(host, pg, dres) {
  const a = pg.affordability;
  clear(host);
  const rows = [];
  if (a.budget != null) rows.push(["Your budget", a.budget, `${PERIOD_TEXT(a.budget_period)} · from your profile`, "b"]);
  if (a.cost_of_attendance) rows.push(["Cost of attendance", a.cost_of_attendance.value, `${a.cost_of_attendance.period} · one year, official`, "c"]);
  const max = Math.max(...rows.map(r => r[1]), 1);
  const head = a.comparable
    ? el("div", { class: `dgap ${a.status}` }, el("div", { class: "xs k", text: a.gap >= 0 ? "Headroom per year" : "Shortfall per year" }),
        el("div", { class: "big", text: fmtUSD(Math.abs(a.gap)) }), el("div", { class: "small", text: a.reason }))
    : el("div", { class: "dgap none" }, el("div", { class: "big", text: "No official total cost to compare" }), el("div", { class: "small", text: a.reason }),
        a.estimate ? el("div", { class: "dest" }, el("span", { class: "pvtag warn", text: "Estimate" }),
          el("p", {}, `${a.estimate.publisher} estimates ${fmtUSD(a.estimate.value)} for one year (${a.estimate.period}). Against your ${fmtUSD(a.budget)} per-year budget that would be `,
            el("b", { text: a.estimate.gap_estimate >= 0 ? `${fmtUSD(a.estimate.gap_estimate)} of headroom` : `a ${fmtUSD(-a.estimate.gap_estimate)} shortfall` }),
            " — an estimate, not the school's own figure. ", extLink(a.estimate.source_url, "See the estimate"))) : null);
  put(host, el("div", { class: "dcard" },
    el("p", { class: "small muted", text: `${pg.program_name}. Budget minus published one-year cost of attendance — computed in code, only when both are per academic year.` }),
    head,
    a.comparable ? el("div", { class: "dbars", role: "img", "aria-label": `Budget ${fmtUSD(a.budget)} versus cost of attendance ${fmtUSD(a.cost_of_attendance.value)}` },
      rows.map(([k, v, sub, cls]) => el("div", { class: "dbar" }, el("div", { class: "spread small" }, el("span", { text: k }), el("b", { text: fmtUSD(v) })),
        el("div", { class: "track" }, el("i", { class: cls, style: `width:${(v / max) * 100}%` })), el("div", { class: "xs muted", text: sub })))) : null,
    el("ul", { class: "dlist" },
      el("li", {}, el("span", { class: "muted", text: "Cost of attendance: " }), a.cost_of_attendance ? `${fmtUSD(a.cost_of_attendance.value)} (${a.cost_of_attendance.period})` : "Not published on the official pages checked",
        a.cost_of_attendance ? el("div", {}, srcLinks(dres, a.cost_of_attendance.evidence_ids)) : null),
      el("li", {}, el("span", { class: "muted", text: "Tuition: " }), a.tuition ? `${fmtUSD(a.tuition.value)} (${a.tuition.period}) — tuition only, excludes living costs` : "Not published on the official pages checked",
        a.tuition ? el("div", {}, srcLinks(dres, a.tuition.evidence_ids)) : null)),
    el("p", { class: "xs muted", text: "Scholarships and aid aren't included: none are assumed. Check each school's financial aid page." })));
}
function drawIntl(host, pg, dres) {
  clear(host);
  if (!pg.feasibility) {   // applicant said they don't need U.S. work authorization
    put(host, el("p", { class: "small muted", text: "Not shown: this applicant doesn't need U.S. work authorization, so STEM designation and employer visa evidence aren't relevant to the plan." }));
    return;
  }
  const fe = pg.feasibility, s = fe.stem;
  const io = fe.international_outcomes;
  put(host, el("div", { class: "dcols three" },
    el("div", { class: "dcard" }, el("h3", { text: "STEM designation" }),
      s.status === "verified" ? [el("span", { class: `dtag ${s.designated ? "ok" : ""}`, text: s.designated ? (s.partial ? "Verified · some tracks only" : "Verified · designated") : "Verified · not designated" }),
        el("p", { class: "small", text: s.scope }), srcLinks(dres, s.evidence_ids)]
        : [el("span", { class: "dtag warn", text: "Unknown" }), el("p", { class: "small muted", text: "No official source establishes STEM status for this program." })]),
    el("div", { class: "dcard" }, el("h3", { text: "International outcomes" }),
      io ? [el("span", { class: `dtag ${io.kind === "figure" ? "ok" : "warn"}`, text: io.kind === "figure" ? "Official figure" : "No outcome figure published" }), el("p", { class: "small", text: `${io.value && typeof io.value === "object" ? Object.entries(io.value).map(([k, x]) => `${k.replace(/_/g, " ")}: ${x}`).join(" · ") : io.value}${io.period ? ` (${io.period})` : ""}` }), srcLinks(dres, io.evidence_ids)]
        : [el("span", { class: "dtag warn", text: "Not published" }), el("p", { class: "small muted", text: "No official international-student outcome figure with a cohort and definition was found." })]),
    el("div", { class: "dcard" }, el("h3", { text: "Employer H-1B filing history" }),
      el("span", { class: "dtag warn", text: "Not school sponsorship" }),
      el("p", { class: "small dwarn", text: "This is employer filing history, not sponsorship by the school. Past filings don't guarantee that any employer will sponsor you; employers decide case by case." }),
      fe.sponsorship.status === "employer_specific" ? [el("p", { class: "small", text: factValue({ fact: "sponsorship", status: "verified", value: fe.sponsorship.value }) }), srcLinks(dres, fe.sponsorship.evidence_ids)] : null,
      fe.h1b_history?.status === "ok" ? more("View employer evidence", h1bBlock(fe.h1b_history, { limit: 5 })) : h1bBlock(fe.h1b_history, { limit: 5 }))),
    note("warn", "STEM ≠ sponsorship.", fe.notes.join(" ")));
}
function drawWorkspace(host, d, dres, runId, selectProgram, remote = null, weekHost = null, timing = planTiming(d.programs)) {
  const w = d.workspace, key = `ac-workspace-${d.run.run_id || runId}`;
  const byId = Object.fromEntries(w.tasks.map(t => [t.id, t]));
  const valid = new Set(w.tasks.map(t => t.id));
  let done = {};
  if (remote) { for (const id of remote) if (valid.has(id)) done[id] = true; }
  else { try { const raw = JSON.parse(localStorage.getItem(key)) || {}; for (const id of Object.keys(raw)) if (valid.has(id) && raw[id] === true) done[id] = true; } catch { done = {}; } }
  const history = [];
  let confirmReset = false;
  const runKey = d.run.run_id || runId;
  const save = () => {
    if (!remote) { localStorage.setItem(key, JSON.stringify(done)); return; }
    api(`/api/account/progress/${encodeURIComponent(runKey)}`, { method: "PUT", body: JSON.stringify({ done: Object.keys(done) }) })
      .catch(err => toast(`Progress not saved to your account: ${err.message}`));
  };
  const change = next => { history.push({ ...done }); done = next; save(); draw(); };
  const order = w.phases.flatMap(ph => ph.task_ids);
  let planOpen = false;
  const planWeek = t => `Plan week ${t.week}`;
  const wk = w.weekly || null, act = id => wk?.actions?.[id];
  const TIER_TEXT = { must: "Must do", should: "Should do", optional: "Optional" };
  const unlockKey = `ac-weeks-${d.run.run_id || runId}`;
  let unlocked = 1, viewWeek = null, showAllWeek = false;
  const plainWhy = w2 => w2.replace(/^Gap flagged by the Strategy Planner \(AI-inferred\): /, "From your profile: ");
  try { unlocked = Math.max(1, Number(localStorage.getItem(unlockKey)) || 1); } catch { /* storage blocked: start at week 1 */ }
  const toggle = (id, isDone) => () => { const nx = { ...done }; if (isDone) delete nx[id]; else nx[id] = true; change(nx); };
  const taskRow = (id, nextId) => { const t = byId[id], isDone = !!done[id];
    return el("div", { class: `dtask${isDone ? " done" : ""}${id === nextId ? " next" : ""}`, "data-task": id },
      el("div", {}, el("div", { text: t.text }), el("div", { class: "xs muted", text: [planWeek(t), act(id) ? `${TIER_TEXT[act(id).tier]} · ~${act(id).minutes} min (est.)` : `${t.priority} priority`,
        act(id)?.moved_from ? "moved up to week 1" : null, id === nextId ? "next up" : null].filter(Boolean).join(" · ") })),
      el("button", { type: "button", class: "btn btn-quiet tbtn", "aria-pressed": isDone ? "true" : "false", "aria-label": `${isDone ? "Mark not done" : "Mark complete"}: ${t.text}`,
        onclick: toggle(id, isDone), text: isDone ? "Done ✓" : "Mark complete" })); };
  /* Weekly action system: one week at a time, at most 5 priority actions split into must / should / optional, each with
     a planning-estimate duration, the reason it matters and a completion control. The next week unlocks only after the
     applicant confirms they understand the current one. */
  function drawWeek() {
    if (!wk?.weeks?.length) {   // older payloads without the weekly layer: fall back to the next open tasks
      const nextId = order.find(id => !done[id]), open = order.filter(id => !done[id]).slice(0, 4);
      put(clear(weekHost), el("div", { class: "dtasks" }, open.map(id => taskRow(id, nextId)))); return;
    }
    const weeks = wk.weeks, last = weeks[weeks.length - 1].week;
    unlocked = Math.min(unlocked, weeks.length);
    const shown = weeks[Math.min(viewWeek ?? unlocked, unlocked) - 1];
    const row = id => { const t = byId[id], a = act(id), isDone = !!done[id];
      return el("li", { class: `dwk-item${isDone ? " done" : ""}`, "data-task": id },
        el("button", { type: "button", class: "dwk-check", "aria-pressed": isDone ? "true" : "false", "aria-label": `${isDone ? "Mark not done" : "Mark done"}: ${t.text}`,
          onclick: toggle(id, isDone) }, isDone ? "✓" : ""),
        el("div", {}, el("div", { class: "dwk-text", text: t.text }),
          el("div", { class: "dwk-why" }, el("b", { text: "Why: " }), plainWhy(a.why)),
          el("div", { class: "dwk-meta", text: [`About ${a.minutes} min · planning estimate`, a.moved_from ? `moved up from plan week ${a.moved_from} so week 1 covers the essentials` : null].filter(Boolean).join(" · ") }))); };
    const group = (tier, ids) => ids.length ? el("div", { class: `dwk-group ${tier}` }, el("h4", {}, el("span", { class: `dtag ${tier === "must" ? "ok" : tier === "optional" ? "" : "ai"}`, text: TIER_TEXT[tier] })),
      el("ul", { class: "dwk-list" }, ids.map(row))) : null;
    const prio = shown.priority, INITIAL = 3, visible = showAllWeek ? prio : prio.slice(0, INITIAL);
    const must = visible.filter(i => act(i).tier === "must"), should = visible.filter(i => act(i).tier === "should");
    const allMust = prio.filter(i => act(i).tier === "must");
    const doneMust = allMust.filter(i => done[i]).length, hrs = Math.round(shown.minutes / 30) / 2;
    put(clear(weekHost),
      el("div", { class: "dwk-tabs", role: "group", "aria-label": "Plan weeks" },
        weeks.slice(0, unlocked).map(x => el("button", { type: "button", class: "chip", "aria-pressed": x.week === shown.week ? "true" : "false",
          onclick: () => { viewWeek = x.week; showAllWeek = false; drawWeek(); }, text: `Week ${x.week}` })),
        unlocked < weeks.length ? el("span", { class: "chip locked", "aria-disabled": "true", text: `Week ${weeks[unlocked].week} · locked` }) : null),
      el("div", { class: "spread dwk-head" }, el("b", { text: `Week ${shown.week} of ${last}` }),
        el("span", { class: "small muted", text: `${prio.length} priority actions · about ${hrs} hours · ${doneMust}/${allMust.length} must-dos done` })),
      group("must", must), group("should", should),
      prio.length > INITIAL ? el("button", { type: "button", class: "btn btn-quiet dwk-more", "aria-expanded": showAllWeek ? "true" : "false", onclick: () => { showAllWeek = !showAllWeek; drawWeek(); },
        text: showAllWeek ? "Show fewer" : `Show ${prio.length - INITIAL} more this week` }) : null,
      showAllWeek ? group("optional", shown.optional) : null,
      shown.more.length ? more(`Also planned this week (${shown.more.length})`, el("ul", { class: "dwk-list" }, shown.more.map(row))) : null,
      shown.week === weeks[unlocked - 1].week && unlocked < weeks.length
        ? el("div", { class: "dwk-gate" }, el("p", { class: "small", text: `When this week's plan is clear to you, unlock week ${weeks[unlocked].week}. You don't need to finish every task first.` }),
            el("button", { type: "button", class: "btn btn-secondary", onclick: () => { unlocked += 1; viewWeek = unlocked; showAllWeek = false; try { localStorage.setItem(unlockKey, String(unlocked)); } catch { /* not remembered */ } drawWeek(); },
              text: `I understand week ${shown.week} — show week ${weeks[unlocked].week}` }))
        : null,
      el("p", { class: "xs muted", text: `${wk.estimate_note} ${Object.keys(done).length} of ${w.tasks.length} plan tasks done; the full plan is under Detailed evidence.` }));
  }
  function draw() {
    clear(host);
    if (weekHost) drawWeek();
    const n = Object.keys(done).length, total = w.tasks.length, pct = total ? Math.round((n / total) * 100) : 0;
    const nextId = order.find(id => !done[id]);
    put(host, el("div", { class: "dcard dprog-card" },
      el("div", { class: "spread" }, el("b", { text: `${n} of ${total} tasks done` }), el("span", { class: "small muted", text: `${pct}%` })),
      el("div", { class: "track", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(total), "aria-valuenow": String(n), "aria-label": "Tasks completed" }, el("i", { class: "c", style: `width:${pct}%` })),
      nextId ? el("p", { class: "dnext" }, el("span", { class: "dtag ai", text: "Next task" }), " ", byId[nextId].text, el("span", { class: "xs muted", text: ` · ${planWeek(byId[nextId])}` }))
        : el("p", { class: "dnext", text: "All planned tasks are marked done." }),
      el("div", { class: "dactions" },
        el("button", { type: "button", class: "btn btn-secondary", id: "ws-undo", disabled: history.length ? null : true, onclick: () => { done = history.pop(); save(); draw(); }, text: "Undo last change" }),
        confirmReset
          ? [el("button", { type: "button", class: "btn btn-secondary danger", id: "ws-reset-yes", onclick: () => { confirmReset = false; change({}); }, text: "Yes, clear all progress" }),
             el("button", { type: "button", class: "btn btn-quiet", onclick: () => { confirmReset = false; draw(); }, text: "Cancel" })]
          : el("button", { type: "button", class: "btn btn-quiet", id: "ws-reset", disabled: n ? null : true, onclick: () => { confirmReset = true; draw(); }, text: "Reset progress" })),
      el("p", { class: "xs muted", text: remote ? `Saved to your account (${S.user.email}).` : `${w.storage_note}${S.user || !S.config?.accounts_enabled ? "" : " Sign in to keep it in your account."}` }),
      timingNote(timing)));
    const plan = el("details", { class: "more dplan", open: planOpen || null, ontoggle: e => { planOpen = e.target.open; } },
      el("summary", { text: `View the complete ${wk?.weeks?.length ? `${wk.weeks.length}-week ` : ""}plan (${w.tasks.length} tasks in ${w.phases.length} phases)` }));
    for (const ph of w.phases) {
      const k = ph.task_ids.filter(id => done[id]).length;
      put(plan, el("div", { class: `dphase${ph.human_checkpoint ? " human" : ""}` },
        el("div", { class: "spread" }, el("h3", { text: ph.phase }), el("span", { class: "xs muted", text: `${ph.timing.replace(/^Weeks?\b/, m => `Plan ${m.toLowerCase()}`)}${ph.task_ids.length ? ` · ${k}/${ph.task_ids.length}` : ""}` })),
        ph.human_checkpoint ? el("div", { class: "xs hc", text: "Human checkpoint — these decisions are yours." }) : null,
        ph.milestones.length ? el("ul", { class: "small dmiles" }, ph.milestones.map(m => el("li", { text: m }))) : null,
        el("div", { class: "dtasks" }, ph.task_ids.map(id => taskRow(id, nextId)),
          !ph.task_ids.length ? el("p", { class: "small muted", text: "No weekly tasks in this phase — it follows submission." }) : null)));
    }
    put(host, plan);
    /* deadlines + saved programs */
    const saved = [...savedSet()];
    put(host, el("div", { class: "dcols" },
      el("div", { class: "dcard" }, el("h3", { text: "Deadlines" }),
        el("ul", { class: "dlist" }, d.programs.map(pg => { const dl = pg.deadlines;
          const info = deadlineRounds(dl);
          return el("li", {}, el("b", { text: `${SCHOOL[pg.program_id] || pg.program_name}` }),
            dl.status === "verified" ? [el("span", { class: "xs muted", text: ` · ${dl.cycle || "current"} cycle · ` }), dl.source_url ? extLink(dl.source_url, "official page") : null,
              el("ul", { class: "ddl" }, info.rounds.map(r => el("li", { class: r.status }, el("span", { class: `dtag ${DL_TAG[r.status][0]}`, text: DL_TAG[r.status][1] }), " ",
                `${r.name}: ${isISODate(r.date) ? fmtDate(r.date) : "date not stated"}`)))]
              : [" ", el("span", { class: "dtag warn", text: "Unverified" }), " ", dl.status === "not_published" ? "Checked — not published for the current cycle" : "Not checked yet — confirm on the official admissions page"]); })),
        el("p", { class: "xs muted", text: `Passed and upcoming are computed against today's date (${fmtDate(todayISO())}). Deadlines appear only when an official page states them for a specific cycle.` })),
      el("div", { class: "dcard" }, el("h3", { text: "Saved programs" }),
        saved.length ? el("ul", { class: "dlist" }, saved.map(id => { const inList = d.programs.find(pg => pg.program_id === id);
          return el("li", {}, el("b", { text: SCHOOL[id] || id }), " · ",
            inList ? el("button", { type: "button", class: "linkbtn", onclick: () => selectProgram(id), text: "View fit & evidence" }) : el("a", { href: "#/explore", text: "Open in Explore" })); }))
          : el("p", { class: "small muted" }, "You haven't saved any programs. ", el("a", { href: "#/explore", text: "Explore programs" }), " and save the ones you like."),
        S.user ? null : el("p", { class: "xs muted", text: "Saved programs and task progress are kept in this browser only." }))));
  }
  draw();
}

/* ---------------- Ask AdmitCompass copilot ----------------
   Real model calls go through /api/copilot/chat (server holds the key). Conversation lives in this tab only
   (sessionStorage); the server stores nothing. Page context is explicit and visible as removable chips. */
S.ctx = {};
const CP_KEY = "ac-chat";
const cpNewId = () => (crypto.randomUUID ? crypto.randomUUID() : `c-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`);
function cpLoad() {
  try { const c = JSON.parse(sessionStorage.getItem(CP_KEY)); if (c && c.id && Array.isArray(c.messages)) return c; } catch { /* fresh */ }
  return { id: cpNewId(), messages: [] };
}
S.chat = cpLoad();
const cpSave = () => { try { sessionStorage.setItem(CP_KEY, JSON.stringify(S.chat)); } catch { /* not kept */ } };
const CP = { open: false, busy: false, status: null, els: {} };
function setChatContext(ctx) { S.ctx = ctx || {}; if (CP.els.ctx) drawCtx(); if (CP.els.log && !S.chat.messages.length) drawLog(); }
function cpSuggestions() {
  const c = S.ctx, nm = id => SCHOOL[id] || id.replace(/-mba$/, "").replace(/-/g, " ");
  if (c.compare_ids?.length >= 2) return [`Compare ${c.compare_ids.map(nm).join(" and ")} on cost and STEM status.`, "Which of these has published employment outcomes?"];
  if (c.program_id && c.run === "demo") return [`Why is ${nm(c.program_id)} recommended for this profile?`, `Can this applicant afford ${nm(c.program_id)}?`, "What should I do next?"];
  if (c.program_id) return [`What does ${nm(c.program_id)} cost?`, `Is ${nm(c.program_id)} STEM-designated?`, `What do we know about visa sponsorship at ${nm(c.program_id)}?`];
  if (c.run === "demo") return ["Why is MIT Sloan recommended for this profile?", "Compare Yale and Booth for my career goal.", "What do we know about visa sponsorship?", "What should I do next?"];
  return ["Which programs have verified STEM status?", "What do we know about visa sponsorship?", "Compare Yale and Booth on cost.", "How should I choose between the GMAT and GRE?"];
}
function setupCopilot() {
  const launch = el("button", { type: "button", class: "cp-launch", id: "cp-launch", "aria-expanded": "false", "aria-controls": "cp-panel", onclick: () => cpToggle(!CP.open) },
    el("span", { class: "cp-spark", "aria-hidden": "true", text: "✦" }), el("span", { class: "cp-label", text: "Ask AI" }));
  const ctx = el("div", { class: "cp-ctx", "aria-label": "Context sent with your question" });
  const log = el("div", { class: "cp-log", role: "log", "aria-live": "polite", "aria-relevant": "additions", tabindex: "0", "aria-label": "Conversation" });
  const input = el("textarea", { id: "cp-input", rows: "1", maxlength: "1000", placeholder: "Ask about costs, STEM, visas, your plan…", "aria-label": "Your question",
    onkeydown: e => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); cpSend(input.value); } },
    oninput: () => { input.style.height = "auto"; input.style.height = Math.min(140, input.scrollHeight) + "px"; input.style.overflowY = input.scrollHeight > 140 ? "auto" : "hidden"; count.textContent = input.value.length > 800 ? `${input.value.length}/1000` : ""; } });
  const count = el("span", { class: "cp-count", "aria-live": "polite" });
  const send = el("button", { type: "submit", class: "cp-send", "aria-label": "Send question" }, el("span", { "aria-hidden": "true", text: "↑" }));
  const form = el("form", { class: "cp-compose", onsubmit: e => { e.preventDefault(); cpSend(input.value); } }, input, send);
  const sub = el("div", { class: "cp-sub", text: "Answers cite official sources" });
  const panel = el("aside", { class: "cp-panel", id: "cp-panel", role: "dialog", "aria-modal": "false", "aria-labelledby": "cp-title", hidden: true },
    el("div", { class: "cp-head" },
      el("div", { class: "cp-mark", "aria-hidden": "true", text: "✦" }),
      el("div", { class: "cp-titles" }, el("h2", { id: "cp-title", text: "Ask AdmitCompass" }), sub),
      el("button", { type: "button", class: "cp-icon", title: "New conversation", "aria-label": "New conversation", onclick: cpReset, text: "＋" }),
      el("button", { type: "button", class: "cp-icon", "aria-label": "Close assistant", onclick: () => cpToggle(false), text: "×" })),
    ctx, log,
    el("div", { class: "cp-foot" }, form, el("div", { class: "cp-note" }, count,
      el("span", { text: "AI can make mistakes. School facts are cited and unknowns flagged — not admissions or immigration advice." }))));
  panel.addEventListener("keydown", e => { if (e.key === "Escape") { e.stopPropagation(); cpToggle(false); } });
  const themeBtn = document.getElementById("theme-toggle");
  if (themeBtn) themeBtn.before(launch); else document.body.appendChild(launch);   // header row: never floats over content
  document.body.appendChild(panel);
  CP.els = { launch, panel, ctx, log, input, send, sub };
  drawCtx(); drawLog();
  api("/api/copilot/status").then(s => { CP.status = s; sub.textContent = !s.available ? "Unavailable on this server" : s.mode === "mock" ? "Mock mode — no AI calls are made" : "gpt-6-luna · answers cite official sources"; drawLog(); })
    .catch(() => { CP.status = { available: false }; sub.textContent = "Unavailable right now"; });
}
function cpToggle(open) {
  CP.open = open;
  const { panel, launch, input, log } = CP.els;
  panel.hidden = !open; launch.setAttribute("aria-expanded", String(open)); document.body.classList.toggle("cp-open", open);
  if (open) { input.focus(); log.scrollTop = log.scrollHeight; } else launch.focus();
}
function cpReset() {
  S.chat = { id: cpNewId(), messages: [] }; cpSave(); drawLog(); CP.els.input.value = ""; CP.els.input.focus();
}
function drawCtx() {
  const c = S.ctx, box = clear(CP.els.ctx), nm = id => SCHOOL[id] || id;
  const chip = (text, drop) => el("span", { class: "cp-chip" }, text, el("button", { type: "button", "aria-label": `Remove context: ${text}`, onclick: drop, text: "×" }));
  const chips = [];
  if (c.run === "demo") chips.push(chip("Sample analysis", () => setChatContext({ ...S.ctx, run: null })));
  if (c.program_id) chips.push(chip(nm(c.program_id), () => setChatContext({ ...S.ctx, program_id: null })));
  if (c.compare_ids?.length) chips.push(chip(`Comparing ${c.compare_ids.map(nm).join(", ")}`, () => setChatContext({ ...S.ctx, compare_ids: [] })));
  box.hidden = !chips.length;
  if (chips.length) put(box, el("span", { class: "cp-ctx-l", text: "Context:" }), chips);
}
function cpCiteText(text, cites) {
  const byN = Object.fromEntries((cites || []).map(c => [String(c.n), c]));
  return String(text).split("\n").filter(Boolean).map(line => el("p", {}, line.split(/(\[\d+\])/).map(part => {
    const m = /^\[(\d+)\]$/.exec(part), c = m && byN[m[1]];
    return c ? el("a", { class: "cp-cite", href: c.source_url, target: "_blank", rel: "noopener noreferrer", title: `${c.source_title}`, "aria-label": `Source ${c.n}: ${c.source_title}`, text: c.n }) : part;
  })));
}
const CP_TYPE = { sourced: ["ok", "Cited from official pages"], general: ["", "General guidance"], mixed: ["ai", "Sourced + general guidance"], refused: ["warn", "Outside what I can do"] };
function cpMessage(m) {
  if (m.role === "user") return el("div", { class: "cp-msg user" }, el("div", { class: "cp-bubble", text: m.content }));
  if (m.role === "error") return el("div", { class: "cp-msg err", role: "alert" }, el("div", { class: "cp-bubble" }, m.content,
    m.retry ? el("button", { type: "button", class: "linkbtn", onclick: () => { S.chat.messages.pop(); const q = m.retry; S.chat.messages = S.chat.messages.filter((x, i, a) => !(i === a.length - 1 && x.role === "user" && x.content === q)); cpSend(q); }, text: " Try again" }) : null));
  const r = m.meta || {}, [cls, label] = CP_TYPE[r.answer_type] || CP_TYPE.general, u = r.usage || {};
  return el("div", { class: "cp-msg bot" },
    el("div", { class: "cp-bubble" },
      el("div", { class: "cp-meta" }, el("span", { class: `pvtag ${cls}`, text: label }), r.mode === "mock" ? el("span", { class: "pvtag warn", text: "Mock" }) : null),
      cpCiteText(m.content, r.citations),
      r.grounding?.fallback ? el("p", { class: "cp-fb", text: "Shown as sourced facts only — the AI's own wording couldn't be verified against the evidence." }) : null,
      r.next_step ? el("p", { class: "cp-next" }, el("b", { text: "Next step: " }), r.next_step) : null,
      (r.uncertainties || []).length ? el("details", { class: "cp-unc" }, el("summary", { text: `What's uncertain (${r.uncertainties.length})` }),
        el("ul", {}, r.uncertainties.map(x => el("li", { text: x })))) : null,
      (r.citations || []).length ? el("ol", { class: "cp-srcs", "aria-label": "Sources" }, r.citations.map(c => el("li", { value: String(c.n) },
        extLink(c.source_url, c.source_title), el("span", { class: "xs muted", text: ` · ${SCHOOL[c.program_id] || c.program_id}` })))) : null,
      u.model_calls != null ? el("div", { class: "cp-usage", text: u.model_calls === 0 ? "No model call" :
        `${u.model_calls} model call${u.model_calls === 1 ? "" : "s"}${u.input_tokens ? ` · ${fmtInt(u.input_tokens)} in / ${fmtInt(u.output_tokens)} out tokens` : ""} · ${u.elapsed_seconds ?? "—"} s` }) : null));
}
function drawLog() {
  const log = clear(CP.els.log);
  if (!S.chat.messages.length) {
    put(log, el("div", { class: "cp-empty" },
      el("div", { class: "cp-hello", text: "Hi! Ask me anything about MBA programs." }),
      el("p", { class: "small muted", text: "I answer from AdmitCompass's official-source evidence, cite every school fact, and tell you plainly what isn't known." }),
      CP.status && !CP.status.available ? note("warn", "The AI copilot isn't available on this server.", "No model key is configured. Programs and the sample analysis still work.") : null,
      el("div", { class: "cp-sugs", role: "group", "aria-label": "Suggested questions" }, cpSuggestions().map(q => el("button", { type: "button", class: "cp-sug", onclick: () => cpSend(q), text: q })))));
    return;
  }
  put(log, S.chat.messages.map(cpMessage));
  if (CP.busy) put(log, el("div", { class: "cp-msg bot" }, el("div", { class: "cp-bubble cp-typing", role: "status" }, el("span", { class: "dots", "aria-hidden": "true" }, el("i"), el("i"), el("i")), el("span", { class: "sr-only", text: "Thinking…" }), " Checking the evidence…")));
  else if (S.chat.messages[S.chat.messages.length - 1]?.role === "assistant") {
    const next = cpSuggestions().filter(q => !S.chat.messages.some(m => m.content === q)).slice(0, 2);
    if (next.length) put(log, el("div", { class: "cp-sugs inline", role: "group", "aria-label": "Follow-up suggestions" }, next.map(q => el("button", { type: "button", class: "cp-sug", onclick: () => cpSend(q), text: q }))));
  }
  log.scrollTop = log.scrollHeight;
}
async function cpSend(text) {
  const q = String(text || "").trim();
  if (!q || CP.busy) return;
  if (q.length > 1000) { toast("Questions can be up to 1,000 characters."); return; }
  const history = S.chat.messages.filter(m => m.role === "user" || m.role === "assistant").slice(-6).map(m => ({ role: m.role, content: String(m.content).slice(0, 1500) }));
  S.chat.messages.push({ role: "user", content: q }); CP.busy = true; CP.els.input.value = ""; CP.els.input.style.height = "auto";
  CP.els.send.disabled = true; CP.els.input.setAttribute("aria-busy", "true"); drawLog();
  const c = S.ctx, context = {};
  if (c.program_id) context.program_id = c.program_id;
  if (c.compare_ids?.length) context.compare_ids = c.compare_ids.slice(0, 4);
  if (c.run === "demo") context.run = "demo";
  try {
    const r = await api("/api/copilot/chat", { method: "POST", body: JSON.stringify({ conversation_id: S.chat.id, message: q, history, context }), timeoutMs: 120000 });
    S.chat.messages.push({ role: "assistant", content: r.answer, meta: { answer_type: r.answer_type, citations: r.citations, uncertainties: r.uncertainties,
      next_step: r.next_step, grounding: r.grounding, usage: r.usage, mode: r.mode } });
  } catch (err) {
    S.chat.messages.push({ role: "error", content: err.message || "Something went wrong.", retry: err.status === 502 || !err.status ? q : null });
  } finally {
    CP.busy = false; CP.els.send.disabled = false; CP.els.input.removeAttribute("aria-busy"); cpSave(); drawLog(); CP.els.input.focus();
  }
}


boot();
