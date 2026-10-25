"""Build the self-contained deliverables/report.html from deliverables/report_src/report.template.html.

Embeds the local fonts (base64 woff2) and the screenshots (cropped, re-encoded as JPEG, base64), and generates the
token tables and chart from the saved run files, so every number in them is read from the repository and not typed by hand.
No network access and no model calls.

    .venv\\Scripts\\python scripts\\build_report.py
"""
from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "deliverables" / "report_src" / "report.template.html"
OUT = ROOT / "deliverables" / "report.html"
CLEAN = ROOT / "experiments" / "tokenomics" / "clean_runs_analysis.json"
SAVED_RUN = ROOT / "experiments" / "agent_runs" / "20261024T032006Z_fixture-audit-consulting-ghana" / "report.json"
RUNS_PER_USER_PER_MONTH = 4   # same assumption as backend/app/tools/run_record.py
AGENTS = [("pathway_matcher", "Pathway Matcher"), ("evidence_analyst", "Evidence Analyst"),
          ("strategy_planner", "Strategy Planner"), ("skeptic", "Skeptic")]


def fonts() -> str:
    out = []
    for fam, file in (("Inter", "inter-latin-var.woff2"), ("Plus Jakarta Sans", "plus-jakarta-sans-latin-var.woff2")):
        b64 = base64.b64encode((ROOT / "frontend" / "fonts" / file).read_bytes()).decode()
        out.append(f'@font-face{{font-family:"{fam}";src:url(data:font/woff2;base64,{b64}) format("woff2");'
                   f'font-weight:100 900;font-style:normal;font-display:swap}}')
    return "\n".join(out)


def image(spec: str) -> str:
    path, box, maxw = spec.split("|")
    im = Image.open(ROOT / path).convert("RGB")
    x0, y0, x1, y1 = (int(v) for v in box.split(","))
    im = im.crop((x0, y0, x1, y1))
    maxw = int(maxw)
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    elif im.width < 640:   # small crops of low-resolution captures: upscale so print isn't pixelated
        f = min(2.0, maxw / im.width)
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=84, optimize=True)
    alt = Path(path).stem.replace("_", " ")
    return f'<img alt="{alt}" src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}">'


def n(v) -> str:
    return f"{v:,}"


def short(run_dir: str) -> str:
    m = re.match(r"(\d{8})T(\d{6})Z_fixture-([a-z-]+?)(_webui)?$", run_dir)
    who = {"audit-consulting-ghana": "Ghana", "domestic-tech-us": "U.S."}.get(m.group(3), m.group(3))
    return f"{who} {m.group(2)[:2]}:{m.group(2)[2:4]}{' web UI' if m.group(4) else ''}"


def runs_table(clean: dict) -> str:
    rows = ['<table><tr><th>Run (2026-10-24, fixture, UTC start)</th><th>Status</th><th class="r">Requests</th>'
            '<th class="r">Input</th><th class="r">Cached input</th><th class="r">Output</th><th class="r">Reasoning</th>'
            '<th class="r">Total</th><th class="r">Tool calls</th><th class="r">Wall s</th></tr>']
    for rid, r in clean["runs"].items():
        t = r["totals"]
        star = " ★" if rid == SAVED_RUN.parent.name else ""
        rows.append(f'<tr><td>{short(rid)}{star}</td><td>{r["status"].replace("_", " ")}</td><td class="r">{t["model_requests"]}</td>'
                    f'<td class="r">{n(t["input_tokens"])}</td><td class="r">{n(t["cached_input_tokens"])}</td>'
                    f'<td class="r">{n(t["output_tokens"])}</td><td class="r">{n(t["reasoning_tokens_within_output"])}</td>'
                    f'<td class="r">{n(t["input_tokens"] + t["output_tokens"])}</td><td class="r">{t["tool_calls"]}</td>'
                    f'<td class="r">{t["wall_seconds"]:.1f}</td></tr>')
    rows.append("</table>")
    return "".join(rows) + '<p class="cap">★ = the saved run used for the walkthrough (§4) and the default Sample Analysis.</p>'


def runs_chart(clean: dict) -> str:
    runs = list(clean["runs"].items())
    W, H, left, top, bar_h, gap = 470, 34 + 27 * len(runs), 150, 6, 17, 10
    mx = max(r["totals"]["input_tokens"] + r["totals"]["output_tokens"] for _, r in runs)
    scale = (W - left - 60) / mx
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
             f'aria-label="Tokens per measured run" style="width:100%;height:auto;font-family:Inter,system-ui,sans-serif">']
    for i, (rid, r) in enumerate(runs):
        t = r["totals"]
        y = top + i * (bar_h + gap)
        cached, unc, out = t["cached_input_tokens"], t["input_tokens"] - t["cached_input_tokens"], t["output_tokens"]
        x = left
        parts.append(f'<text x="{left - 6}" y="{y + 12}" text-anchor="end" font-size="12" fill="#33415C">{short(rid)}</text>')
        for v, col in ((cached, "#1E40AF"), (unc, "#93B4F5"), (out, "#6D4AE0")):
            w = v * scale
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{col}"/>')
            x += w
        parts.append(f'<text x="{x + 5:.1f}" y="{y + 12}" font-size="11.5" fill="#5A6478">{n(t["input_tokens"] + out)}</text>')
    ly = H - 10
    for i, (lab, col) in enumerate((("Cached input", "#1E40AF"), ("Uncached input", "#93B4F5"), ("Output", "#6D4AE0"))):
        lx = 6 + i * 150
        parts.append(f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" fill="{col}"/>'
                     f'<text x="{lx + 14}" y="{ly}" font-size="12" fill="#33415C">{lab}</text>')
    parts.append("</svg>")
    return "".join(parts)


def agent_table(rep: dict) -> str:
    u = {a["agent"]: a for a in rep["usage_by_agent"]}
    rows = ['<table><tr><th>Agent</th><th class="r">Req.</th><th class="r">Input</th><th class="r">Cached</th>'
            '<th class="r">Output</th><th class="r">Secs</th></tr>']
    tot = {"requests": 0, "input": 0, "cached": 0, "output": 0, "secs": 0.0}
    for key, name in AGENTS:
        a = u[key]
        vals = {"requests": a["calls"], "input": a["input_tokens"],
                "cached": a["cached_input_tokens"], "output": a["output_tokens"], "secs": a["elapsed_seconds"]}
        for k in tot:
            tot[k] += vals[k]
        rows.append(f'<tr><td>{name}</td><td class="r">{vals["requests"]}</td><td class="r">{n(vals["input"])}</td>'
                    f'<td class="r">{n(vals["cached"])}</td><td class="r">{n(vals["output"])}</td><td class="r">{vals["secs"]:.1f}</td></tr>')
    t = rep["totals"]
    assert (tot["requests"], tot["input"], tot["cached"], tot["output"]) == (
        t["model_requests"], t["input_tokens"], t["cached_input_tokens"], t["output_tokens"]), "per-agent sums differ from totals"
    rows.append(f'<tr class="tot"><td>Total</td><td class="r">{tot["requests"]}</td><td class="r">{n(tot["input"])}</td>'
                f'<td class="r">{n(tot["cached"])}</td><td class="r">{n(tot["output"])}</td><td class="r">{tot["secs"]:.1f}</td></tr></table>')
    return "".join(rows)


def proj_table(rep: dict) -> str:
    t = rep["totals"]
    rows = ['<table><tr><th>Scenario</th><th class="r">Runs / month</th><th class="r">Model requests</th><th class="r">Input tokens</th>'
            '<th class="r">Cached input</th><th class="r">Output tokens</th><th class="r">Total tokens</th><th>Cost (USD)</th></tr>']
    for lab, runs in (('Per run <span class="tag t-meas">Measured</span>', 1),
                      ('Per user per month <span class="tag t-est">Estimated</span>', RUNS_PER_USER_PER_MONTH),
                      ('100 users per month <span class="tag t-est">Estimated</span>', 100 * RUNS_PER_USER_PER_MONTH),
                      ('10,000 users per month <span class="tag t-est">Estimated</span>', 10_000 * RUNS_PER_USER_PER_MONTH)):
        rows.append(f'<tr><td>{lab}</td><td class="r">{n(runs)}</td><td class="r">{n(t["model_requests"] * runs)}</td>'
                    f'<td class="r">{n(t["input_tokens"] * runs)}</td><td class="r">{n(t["cached_input_tokens"] * runs)}</td>'
                    f'<td class="r">{n(t["output_tokens"] * runs)}</td><td class="r">{n((t["input_tokens"] + t["output_tokens"]) * runs)}</td>'
                    f'<td>not calculated</td></tr>')
    rows.append("</table>")
    return "".join(rows)


def diagram() -> str:
    navy, teal, ink, muted = "#0B1B3F", "#0E6E86", "#33415C", "#5A6478"
    agents = [("Pathway Matcher", "goal → roles → shortlist", ["search_programs", "get_program_overview"]),
              ("Evidence Analyst", "cost · STEM · outcomes · filings", ["get_program_facts", "get_evidence",
                                                                        "compare_employment_metrics", "get_sponsorship_evidence"]),
              ("Strategy Planner", "test choice · gaps · weekly plan", ["get_program_facts"]),
              ("Skeptic", "challenges weak claims", ["get_evidence", "get_program_facts",
                                                     "compare_employment_metrics", "get_sponsorship_evidence"])]
    W, H, AW = 900, 440, 205
    xs = [10, 238, 466, 694]
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="AdmitCompass agent architecture" '
         'style="font-family:Inter,system-ui,sans-serif">',
         '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         f'<path d="M0,0 L10,5 L0,10 z" fill="{navy}"/></marker>'
         '<marker id="av" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
         '<path d="M0,0 L10,5 L0,10 z" fill="#6D4AE0"/></marker>'
         '<linearGradient id="ag" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1E3A8A"/><stop offset="1" stop-color="#4C1D95"/></linearGradient></defs>']
    # evidence data band
    s.append('<rect x="10" y="4" width="889" height="40" rx="7" fill="#E3F4F8" stroke="#9BD3E1"/>')
    s.append(f'<text x="24" y="21" font-size="13" font-weight="700" fill="{teal}">Evidence data (read only, reached only through tools)</text>'
             f'<text x="24" y="37" font-size="12" fill="{ink}">program evidence store (28 programs) · validated supplementary facts · '
             'DOL FY2025 H-1B LCA filings + reviewed employer aliases</text>')
    for (name, sub, tools), x in zip(agents, xs):
        th = 14 + 16 * len(tools)
        ty = 152 - th
        s.append(f'<line x1="{x + AW / 2}" y1="44" x2="{x + AW / 2}" y2="{ty}" stroke="#9BD3E1" stroke-dasharray="3 3"/>')
        s.append(f'<rect x="{x}" y="{ty}" width="{AW}" height="{th}" rx="5" fill="#F2FAFC" stroke="#9BD3E1"/>')
        for i, tool in enumerate(tools):
            s.append(f'<text x="{x + 9}" y="{ty + 17 + 16 * i}" font-size="11.5" fill="{teal}" font-family="Consolas,monospace">{tool}</text>')
        s.append(f'<line x1="{x + AW / 2}" y1="168" x2="{x + AW / 2}" y2="154" stroke="{teal}" stroke-width="1.3" marker-end="url(#ah)"/>')
        s.append(f'<rect x="{x}" y="168" width="{AW}" height="64" rx="9" fill="url(#ag)"/>'
                 f'<text x="{x + AW / 2}" y="192" text-anchor="middle" font-size="15.5" font-weight="700" fill="#fff">{name}</text>'
                 f'<text x="{x + AW / 2}" y="210" text-anchor="middle" font-size="12" fill="#DDE6FF">{sub}</text>'
                 f'<text x="{x + AW / 2}" y="225" text-anchor="middle" font-size="10.5" fill="#B9C6F5">gpt-6-luna · JSON schema</text>')
    for i in range(3):
        s.append(f'<line x1="{xs[i] + AW}" y1="200" x2="{xs[i + 1] - 2}" y2="200" stroke="{navy}" stroke-width="1.8" marker-end="url(#ah)"/>')
    # revision loop (Skeptic -> any earlier agent; drawn to the Pathway Matcher)
    s.append(f'<path d="M{xs[3] + 60},232 C{xs[3] + 60},284 {xs[0] + 145},284 {xs[0] + 145},236" fill="none" stroke="#6D4AE0" '
             'stroke-width="1.6" stroke-dasharray="6 4" marker-end="url(#av)"/>')
    s.append('<text x="452" y="282" text-anchor="middle" font-size="12" fill="#6D4AE0" font-weight="700">'
             '≤ 1 revision request: re-runs ONE agent and everything after it</text>')
    # profile in / report out
    s.append(f'<line x1="{xs[0] + 50}" y1="318" x2="{xs[0] + 50}" y2="236" stroke="{navy}" stroke-width="1.8" marker-end="url(#ah)"/>')
    s.append(f'<text x="{xs[0] + 58}" y="262" font-size="11.5" fill="{ink}">profile</text>')
    s.append(f'<line x1="{xs[3] + 160}" y1="232" x2="{xs[3] + 160}" y2="316" stroke="{navy}" stroke-width="1.8" marker-end="url(#ah)"/>')
    s.append(f'<text x="{xs[3] + 152}" y="262" text-anchor="end" font-size="11.5" fill="{ink}">findings</text>')
    # orchestrator band
    s.append('<rect x="10" y="318" width="889" height="118" rx="9" fill="#F4F6FA" stroke="#C9D1DF"/>')
    s.append(f'<text x="24" y="340" font-size="14" font-weight="700" fill="{navy}">Orchestrator — plain Python, no model</text>'
             f'<text x="886" y="340" text-anchor="end" font-size="11.5" fill="{ink}">in: validated profile (PII + injection screened) · '
             'out: report + trace + usage</text>')
    items = [("Order + handoffs", "fixed sequence, typed payloads"),
             ("Schema validation", "Pydantic; bounded retry, then fail closed"),
             ("Grounding after every agent", "evidence ids exist · numbers in evidence · no odds or guarantees · statuses recomputed from the store"),
             ("Budget caps per run", "25 requests · 200k tokens · 40 tool calls · 300 s"),
             ("Trace", "metadata only, never prompts or reasoning")]
    cx = [24, 178, 352, 620, 776]
    cw = [140, 160, 255, 145, 118]
    for (h, d), x, w in zip(items, cx, cw):
        s.append(f'<text x="{x}" y="365" font-size="12" font-weight="700" fill="{ink}">{h}</text>')
        line, yy = "", 382
        for wd in d.split(" "):
            if len((line + " " + wd).strip()) * 6.0 > w and line:
                s.append(f'<text x="{x}" y="{yy}" font-size="11" fill="{muted}">{line.strip()}</text>'); yy += 14; line = ""
            line += " " + wd
        s.append(f'<text x="{x}" y="{yy}" font-size="11" fill="{muted}">{line.strip()}</text>')
    s.append("</svg>")
    return "".join(s)


def main() -> None:
    clean = json.loads(CLEAN.read_text(encoding="utf-8"))
    rep = json.loads(SAVED_RUN.read_text(encoding="utf-8"))
    html = SRC.read_text(encoding="utf-8")
    html = html.replace("{{FONTS}}", fonts())
    html = html.replace("{{DIAGRAM}}", diagram())
    html = html.replace("{{RUNS_TABLE}}", runs_table(clean))
    html = html.replace("{{RUNS_CHART}}", runs_chart(clean))
    html = html.replace("{{AGENT_TABLE}}", agent_table(rep))
    html = html.replace("{{PROJ_TABLE}}", proj_table(rep))
    html = re.sub(r"\{\{IMG:([^}]+)\}\}", lambda m: image(m.group(1)), html)
    assert "{{" not in html, "unfilled placeholder"
    assert not re.search(r'(src|href)="(https?:)?//[^"]*\.(css|js|woff2?|png|jpe?g|svg)', html), "remote asset found"
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
