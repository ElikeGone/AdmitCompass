# Render deliverables\diagrams\agent_diagram.mmd to .svg and .png on Windows (Mermaid 11 in headless Edge).
#   powershell -ExecutionPolicy Bypass -File scripts\render_diagram.ps1
# Labels are plain SVG text (htmlLabels:false) so the SVG displays on its own (e.g. embedded in report.html).
$ErrorActionPreference = "Stop"
$D = Join-Path (Split-Path -Parent $PSScriptRoot) "deliverables\diagrams"
$t = Join-Path $env:TEMP ("acdiag-" + (Get-Random)); New-Item -ItemType Directory $t | Out-Null
Invoke-WebRequest "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js" -OutFile "$t\mermaid.min.js" -UseBasicParsing
$utf8 = New-Object System.Text.UTF8Encoding $false
$src = [System.Net.WebUtility]::HtmlEncode((Get-Content "$D\agent_diagram.mmd" -Raw -Encoding utf8))
[IO.File]::WriteAllText("$t\diagram.html", "<!doctype html><html><head><meta charset='utf-8'><style>body{margin:0;background:#fff;font-family:Inter,Segoe UI,Arial}#d{padding:24px}</style><script src='mermaid.min.js'></script></head><body><div id='d' class='mermaid'>$src</div><script>mermaid.initialize({startOnLoad:false,theme:'base',htmlLabels:false,flowchart:{htmlLabels:false,curve:'basis'}});mermaid.run();</script></body></html>", $utf8)
$E = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$uri = "file:///$($t -replace '\\','/')"
$p = Start-Process -FilePath $E -ArgumentList @("--headless=new","--disable-gpu","--user-data-dir=$t\prof","--virtual-time-budget=15000","--dump-dom","$uri/diagram.html") -RedirectStandardOutput "$t\dom.html" -PassThru -WindowStyle Hidden
$p | Wait-Process -Timeout 60 -ErrorAction SilentlyContinue
$svg = [regex]::Match((Get-Content "$t\dom.html" -Raw -Encoding utf8), '<svg[\s\S]*?</svg>').Value
if (-not $svg) { throw "Mermaid did not render" }
[IO.File]::WriteAllText("$D\agent_diagram.svg", $svg, $utf8); Copy-Item "$D\agent_diagram.svg" $t
$vb = [regex]::Match($svg, 'viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"'); $w = [int][double]$vb.Groups[1].Value; $h = [int][double]$vb.Groups[2].Value
[IO.File]::WriteAllText("$t\static.html", "<!doctype html><html><body style='margin:0;background:#fff'><div style='padding:24px'><img src='agent_diagram.svg' style='width:${w}px'></div></body></html>", $utf8)
$p = Start-Process -FilePath $E -ArgumentList @("--headless=new","--disable-gpu","--hide-scrollbars","--user-data-dir=$t\prof2","--window-size=$($w+48),$($h+48)","--screenshot=`"$D\agent_diagram.png`"","$uri/static.html") -PassThru -WindowStyle Hidden
$p | Wait-Process -Timeout 60 -ErrorAction SilentlyContinue
Get-ChildItem $D -Filter "agent_diagram.*" | Select-Object Name, Length
