"""Build the self-contained deliverables/slides.html from deliverables/slides_src/slides.template.html.

Inlines reveal.js 6.0.2 (vendored, MIT licence), the local fonts and the screenshots (cropped, JPEG, base64), and generates
the architecture diagram, token chart and projection table from the saved run files. No network access, no model calls.

    .venv\\Scripts\\python scripts\\build_slides.py
"""
from __future__ import annotations

import base64
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_report import CLEAN, SAVED_RUN, RUNS_PER_USER_PER_MONTH, fonts, n, short  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "deliverables" / "slides_src" / "slides.template.html"
VENDOR = ROOT / "deliverables" / "slides_src" / "vendor" / "reveal.js-6.0.2"
OUT = ROOT / "deliverables" / "slides.html"


def image(spec: str) -> str:
    path, box, maxw, cls = (spec.split("|") + [""])[:4]
    im = Image.open(ROOT / path).convert("RGB")
    x0, y0, x1, y1 = (int(v) for v in box.split(","))
    im = im.crop((x0, y0, x1, y1))
    maxw = int(maxw)
    if im.width > maxw:
        im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=86, optimize=True)
    alt = Path(path).stem.replace("_", " ")
    return (f'<img class="{cls}" alt="{alt}" style="width:100%;height:auto" '
            f'src="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}">')


def arch() -> str:
    W, H = 1456, 560
    navy, ink, muted = "#0E1630", "#EEF2FF", "#9AA6C8"
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="AdmitCompass architecture" '
         'style="width:100%;height:auto;display:block;margin-top:14px;font-family:Inter,system-ui,sans-serif">',
         '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
         '<path d="M0,0 L10,5 L0,10 z" fill="#93A4D6"/></marker>'
         '<marker id="av" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
         '<path d="M0,0 L10,5 L0,10 z" fill="#A78BFA"/></marker>'
         '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1D4ED8"/><stop offset="1" stop-color="#6D28D9"/></linearGradient></defs>']

    def box(x, y, w, h, title, sub, fill=navy, stroke="#2B3866", tc=ink, sc=muted, ts=23, ss=16):
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        s.append(f'<text x="{x + w / 2}" y="{y + h / 2 - (6 if sub else -8)}" text-anchor="middle" font-size="{ts}" font-weight="700" fill="{tc}" '
                 'font-family="Plus Jakarta Sans,Inter,sans-serif">' + title + '</text>')
        for i, line in enumerate(sub):
            s.append(f'<text x="{x + w / 2}" y="{y + h / 2 + 20 + i * 19}" text-anchor="middle" font-size="{ss}" fill="{sc}">{line}</text>')

    def arrow(x1, y1, x2, y2):
        s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#93A4D6" stroke-width="2.2" marker-end="url(#a)"/>')

    cy = 190
    box(0, cy - 60, 170, 120, "User profile", ["validated, PII +", "injection screened"])
    arrow(172, cy, 206, cy)
    box(210, cy - 60, 190, 120, "Orchestrator", ["plain code, no model", "order · handoffs · caps"], stroke="#3B82F6")
    arrow(402, cy, 436, cy)
    # agents group
    s.append('<rect x="440" y="40" width="590" height="320" rx="18" fill="rgba(59,130,246,.06)" stroke="#2F4C9A" stroke-dasharray="6 5"/>')
    s.append(f'<text x="458" y="70" font-size="16" font-weight="700" fill="#93C5FD" letter-spacing="1.5">AGENTS + EVIDENCE</text>')
    for i, (name, sub) in enumerate((("Pathway Matcher", ["goal → roles →", "shortlist"]),
                                     ("Evidence Analyst", ["cost · STEM ·", "outcomes · filings"]),
                                     ("Strategy Planner", ["test choice · gaps", "· weekly plan"]))):
        x = 458 + i * 190
        box(x, 90, 174, 118, name, sub, fill="url(#g)", stroke="#4F6BD8", sc="#DCE4FF", ts=18.5, ss=15)
        if i < 2:
            arrow(x + 175, 149, x + 188, 149)
    s.append('<rect x="458" y="232" width="554" height="108" rx="12" fill="rgba(34,211,238,.08)" stroke="#1F6F86"/>')
    s.append('<text x="735" y="262" text-anchor="middle" font-size="17" font-weight="700" fill="#67E8F9">Read-only tools → validated evidence</text>')
    s.append(f'<text x="735" y="290" text-anchor="middle" font-size="16" fill="{muted}">program evidence store (28 programs) ·</text>')
    s.append(f'<text x="735" y="312" text-anchor="middle" font-size="16" fill="{muted}">supplementary facts · DOL FY2025 H-1B filings</text>')
    for i in range(3):
        s.append(f'<line x1="{545 + i * 190}" y1="208" x2="{545 + i * 190}" y2="230" stroke="#1F6F86" stroke-width="2" stroke-dasharray="3 3"/>')
    arrow(1032, cy, 1066, cy)
    box(1070, cy - 60, 170, 120, "Skeptic", ["challenges weak", "claims · ≤1 revision"], fill="url(#g)", stroke="#8B5CF6", sc="#E9DDFF")
    arrow(1242, cy, 1272, cy)
    box(1276, cy - 60, 180, 120, "Recommendation", ["shortlist · evidence", "· weekly plan"], stroke="#34D399", ts=19)
    s.append('<path d="M1155,130 C1155,8 735,8 735,38" fill="none" stroke="#A78BFA" stroke-width="2" stroke-dasharray="7 5" marker-end="url(#av)"/>')
    s.append('<text x="1166" y="104" font-size="16" fill="#C4B5FD" font-weight="700">≤ 1 revision</text>')
    s.append('<text x="1166" y="123" font-size="16" fill="#C4B5FD" font-weight="700">request</text>')
    # guardrail band
    s.append('<rect x="0" y="384" width="1456" height="70" rx="14" fill="rgba(52,211,153,.07)" stroke="#1E6B52"/>')
    s.append('<text x="24" y="414" font-size="19" font-weight="700" fill="#6EE7B7">After every agent (code):</text>'
             f'<text x="268" y="414" font-size="19" fill="{ink}">schema check · evidence ids exist · numbers in evidence · no odds or guarantees</text>')
    s.append('<text x="24" y="440" font-size="19" font-weight="700" fill="#6EE7B7">Caps per run:</text>'
             f'<text x="160" y="440" font-size="19" fill="{ink}">25 requests · 200k tokens · 40 tool calls · 300 s</text>')
    # copilot lane
    s.append('<rect x="0" y="474" width="1456" height="82" rx="14" fill="rgba(139,92,246,.08)" stroke="#5B3FA8" stroke-dasharray="6 5"/>')
    s.append('<text x="24" y="506" font-size="19" font-weight="700" fill="#C4B5FD">Separate path · Ask AI copilot</text>'
             f'<text x="24" y="534" font-size="18" fill="{ink}">question → keyword retrieval (≤40 facts) → 1 model call → grounding → ≤1 repair → '
             'else a list of sourced facts. No agents, no tools.</text>')
    s.append("</svg>")
    return "".join(s)


def chart(clean: dict) -> str:
    runs = list(clean["runs"].items())
    W, left, bar, gap = 470, 170, 22, 13
    H = 18 + len(runs) * (bar + gap) + 30
    mx = max(r["totals"]["input_tokens"] + r["totals"]["output_tokens"] for _, r in runs)
    sc = (W - left - 86) / mx
    s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Tokens per measured run" '
         'style="width:100%;height:auto;display:block;font-family:Inter,system-ui,sans-serif">']
    for i, (rid, r) in enumerate(runs):
        t = r["totals"]
        y = 10 + i * (bar + gap)
        star = rid == SAVED_RUN.parent.name
        fill, weight, mark = ("#fff", ' font-weight="700"', " ★") if star else ("#C9D3F2", "", "")
        s.append(f'<text x="{left - 8}" y="{y + 16}" text-anchor="end" font-size="17" fill="{fill}"{weight}>{short(rid)}{mark}</text>')
        x = left
        for v, col in ((t["cached_input_tokens"], "#2563EB"), (t["input_tokens"] - t["cached_input_tokens"], "#7FA7F5"), (t["output_tokens"], "#A78BFA")):
            s.append(f'<rect x="{x:.1f}" y="{y}" width="{v * sc:.1f}" height="{bar}" rx="3" fill="{col}"/>')
            x += v * sc
        s.append(f'<text x="{x + 6:.1f}" y="{y + 16}" font-size="17" fill="#C9D3F2">{round((t["input_tokens"] + t["output_tokens"]) / 1000)}k</text>')
    ly = H - 8
    for i, (lab, col) in enumerate((("cached input", "#2563EB"), ("uncached input", "#7FA7F5"), ("output", "#A78BFA"))):
        lx = 8 + i * 156
        s.append(f'<rect x="{lx}" y="{ly - 12}" width="13" height="13" rx="2" fill="{col}"/><text x="{lx + 19}" y="{ly}" font-size="15" fill="#C9D3F2">{lab}</text>')
    s.append("</svg>")
    return "".join(s)


def proj(rep: dict) -> str:
    t = rep["totals"]
    total = t["input_tokens"] + t["output_tokens"]
    rows = ['<table class="t" style="font-size:20px"><tr><th>Scenario</th><th class="r">Runs / mo</th><th class="r">Total tokens</th></tr>']
    for lab, runs in (("1 user", RUNS_PER_USER_PER_MONTH), ("100 users", 100 * RUNS_PER_USER_PER_MONTH),
                      ("10,000 users", 10_000 * RUNS_PER_USER_PER_MONTH)):
        rows.append(f'<tr><td>{lab}</td><td class="r">{n(runs)}</td><td class="r">{n(total * runs)}</td></tr>')
    rows.append("</table>")
    return "".join(rows)


def main() -> None:
    clean = json.loads(CLEAN.read_text(encoding="utf-8"))
    rep = json.loads(SAVED_RUN.read_text(encoding="utf-8"))
    html = SRC.read_text(encoding="utf-8")
    css = (VENDOR / "reveal.css").read_text(encoding="utf-8")
    js = (VENDOR / "reveal.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    for k, v in (("{{REVEAL_CSS}}", css), ("{{FONTS}}", fonts()), ("{{ARCH}}", arch()), ("{{CHART}}", chart(clean)), ("{{PROJ}}", proj(rep))):
        html = html.replace(k, v)
    html = re.sub(r"\{\{IMG:([^}]+)\}\}", lambda m: image(m.group(1)), html)
    html = html.replace("{{REVEAL_JS}}", js)   # last, so nothing inside the library is treated as a placeholder
    assert "{{IMG" not in html and "{{ARCH}}" not in html, "unfilled placeholder"
    assert not re.search(r'(src|href)="(https?:)?//[^"]*\.(css|js|woff2?|png|jpe?g|svg)', html), "remote asset found"
    assert html.count("<section data-title=") == 10, "expected exactly 10 slides"
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
