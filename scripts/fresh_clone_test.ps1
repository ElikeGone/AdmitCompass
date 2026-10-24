# Fresh-clone test (Windows PowerShell).
#   powershell -ExecutionPolicy Bypass -File scripts\fresh_clone_test.ps1 [-RepoUrl https://github.com/<you>/<repo>.git]
# With -RepoUrl: real `git clone`. Without: copies this working tree as a clone would contain it (git-ignored paths excluded).
# Then: puts a .env ONE LEVEL ABOVE the repo, follows README.md steps exactly, starts the app, checks /health, records timing.
param([string]$RepoUrl = "", [int]$Port = 8766)
$ErrorActionPreference = "Stop"
$Src = Split-Path -Parent $PSScriptRoot
$Work = Join-Path $env:TEMP ("acclone-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$Repo = Join-Path $Work "repo"
$Log = Join-Path $Src "experiments\fresh_clone_test.md"
$sw = [Diagnostics.Stopwatch]::StartNew()
function Step($m) { Write-Host ("[{0}s] {1}" -f [int]$sw.Elapsed.TotalSeconds, $m) }

New-Item -ItemType Directory -Force $Work | Out-Null
if ($RepoUrl) {
  Step "git clone $RepoUrl"; git clone --depth 1 $RepoUrl $Repo; $Mode = "git clone of $RepoUrl"
} else {
  Step "no repo URL: copying working tree as a clone (excluding git-ignored paths)"
  robocopy $Src $Repo /E /NFL /NDL /NJH /NJS /NP /XD .venv .git __pycache__ .pytest_cache logs `
    (Join-Path $Src "data\app") (Join-Path $Src "data\sponsorship\raw") (Join-Path $Src "data\sources\cache") (Join-Path $Src "experiments\outputs") `
    /XF .env | Out-Null
  $Mode = "working-tree copy (no git remote yet)"
}
# Placeholder key (not a real key): /health only reports whether a key was loaded; no model call is made.
Set-Content -Path (Join-Path $Work ".env") -Value "PORTKEY_API_KEY=fresh-clone-placeholder-not-a-real-key" -Encoding ascii
Step ".env placed one level ABOVE the repo: $Work\.env"

Set-Location $Repo
Step "README step: py -3 -m venv .venv"; py -3 -m venv .venv
Step "README step: pip install -r requirements.txt"; & .\.venv\Scripts\python -m pip install -q -r requirements.txt
$tInstall = [int]$sw.Elapsed.TotalSeconds
Step "README step: start uvicorn on port $Port"
$server = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$Port" -PassThru -WindowStyle Hidden
$health = $null
for ($i = 0; $i -lt 60; $i++) { try { $health = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2; break } catch { Start-Sleep 1 } }
$tReady = [int]$sw.Elapsed.TotalSeconds
$homeCode = try { (Invoke-WebRequest "http://127.0.0.1:$Port/" -UseBasicParsing).StatusCode } catch { 0 }
$progCode = try { (Invoke-WebRequest "http://127.0.0.1:$Port/api/programs" -UseBasicParsing).StatusCode } catch { 0 }
Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
$ok = $health -and $health.status -eq "ok"
$key = if ($health) { $health.api_key_configured } else { $false }
$result = if ($ok -and $key -and $homeCode -eq 200 -and $progCode -eq 200) { "PASS" } else { "FAIL" }
Step "health ok=$ok api_key_configured=$key home=$homeCode programs=$progCode -> $result"
$pyv = & .\.venv\Scripts\python --version
Add-Content -Path $Log -Encoding utf8 -Value @(
  "",
  "## $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')) - $result (Windows, PowerShell script)",
  "- Mode: $Mode; Python: $pyv",
  "- .env one level above the repo; /health ok=$ok, api_key_configured=$key; GET / = $homeCode; GET /api/programs = $progCode",
  "- Time to installed: ${tInstall}s; time to app answering /health: ${tReady}s (limit: 600s)")
Set-Location $Src
Remove-Item -Recurse -Force $Work -ErrorAction SilentlyContinue
if ($result -ne "PASS") { exit 1 }
