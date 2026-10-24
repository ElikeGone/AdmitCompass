"""macOS / Linux: render deliverables/diagrams/agent_diagram.mmd to SVG and PNG with Mermaid in headless Chrome/Chromium.

    .venv\\Scripts\\python scripts\\render_diagram.py

Mermaid (mermaid@11) is downloaded once into a temp folder next to the page. On Windows the browser is launched through
PowerShell. On Windows prefer scripts/render_diagram.ps1 (the route used for the committed SVG/PNG).
"""
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "deliverables" / "diagrams" / "agent_diagram.mmd"
BROWSERS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            shutil.which("google-chrome") or "", shutil.which("chromium") or "", shutil.which("chromium-browser") or ""]
browser = next((b for b in BROWSERS if b and Path(b).exists()), None)
if not browser:
    sys.exit("No Edge/Chrome/Chromium found.")
PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#fff;font-family:Inter,Segoe UI,Arial}#d{padding:24px}</style>
<script src="mermaid.min.js"></script></head><body><div id="d" class="mermaid">%s</div>
<script>mermaid.initialize({startOnLoad:false, theme:"base", htmlLabels:false, flowchart:{htmlLabels:false, curve:"basis"}}); mermaid.run();</script></body></html>"""


def run_browser(args: list[str], stdout_file: Path | None) -> None:
    if os.name == "nt":
        # Start-Process joins arguments with spaces without quoting, so quote any argument that contains a space
        arglist = ",".join("'" + (f'"{a}"' if " " in a else a).replace("'", "''") + "'" for a in args)
        redirect = f" -RedirectStandardOutput '{stdout_file}'" if stdout_file else ""
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"Start-Process -FilePath '{browser}' -ArgumentList @({arglist}){redirect} -Wait -WindowStyle Hidden"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        with (stdout_file.open("w", encoding="utf-8") if stdout_file else open(os.devnull, "w")) as fh:
            subprocess.run([browser, *args], stdout=fh, stderr=subprocess.DEVNULL)


with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
    d = Path(d)
    urllib.request.urlretrieve("https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js", d / "mermaid.min.js")
    page = d / "diagram.html"
    page.write_text(PAGE % html.escape(SRC.read_text(encoding="utf-8")), encoding="utf-8")
    common = ["--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={d / 'prof'}", "--virtual-time-budget=15000"]
    run_browser(common + ["--dump-dom", page.as_uri()], d / "dom.html")
    dom = (d / "dom.html").read_text(encoding="utf-8", errors="replace") if (d / "dom.html").exists() else ""
    m = re.search(r"<svg[\s\S]*?</svg>", dom)
    if not m:
        sys.exit("Mermaid did not render (no <svg> in the page).")
    svg = m.group(0)
    if "xmlns=" not in svg[:300]:
        svg = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
    SRC.with_suffix(".svg").write_text(svg, encoding="utf-8")
    w = re.search(r"max-width:\s*([\d.]+)px", svg)
    width = int(float(w.group(1))) + 60 if w else 1800
    # PNG from a static page showing the finished SVG (no scripts, so the headless browser exits promptly)
    shutil.copy(SRC.with_suffix(".svg"), d / "agent_diagram.svg")
    static = d / "static.html"
    static.write_text(f"<!doctype html><html><body style='margin:0;background:#fff'><div style='padding:24px'>"
                      f"<img src='agent_diagram.svg' style='width:{width - 60}px'></div></body></html>", encoding="utf-8")
    h = re.search(r'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"', svg)
    height = int(float(h.group(2)) * (width - 60) / float(h.group(1))) + 60 if h else 1150
    run_browser([a for a in common if not a.startswith("--virtual-time")] +
                [f"--window-size={width},{height}", f"--screenshot={SRC.with_suffix('.png')}", static.as_uri()], None)
print("wrote", SRC.with_suffix(".svg"), "and", SRC.with_suffix(".png"))
