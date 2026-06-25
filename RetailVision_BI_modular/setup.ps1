# Setup RetailVision BI — Windows PowerShell (5.1 et 7+)
# Selectionne Python 3.10-3.12 (3.13/3.14 = trop recent pour les libs IA), installe 3.12 si besoin.
$ErrorActionPreference = "Stop"

function Get-CompatiblePython {
    $prev = $ErrorActionPreference; $ErrorActionPreference = "SilentlyContinue"
    $list = (& py -0p 2>$null) | Out-String
    $ErrorActionPreference = $prev
    foreach ($v in @("3.12", "3.11", "3.10")) {
        if ($list -match [regex]::Escape("3.$($v.Split('.')[1])")) { return "-$v" }
    }
    return $null
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Le launcher 'py' est introuvable. Installe Python 3.12 : https://www.python.org/downloads/release/python-3127/" -ForegroundColor Red
    exit 1
}

$sel = Get-CompatiblePython
if (-not $sel) {
    Write-Host "Aucun Python 3.10-3.12 trouve. Installation de Python 3.12 via le launcher…" -ForegroundColor Yellow
    try { py install 3.12 } catch { }
    $sel = Get-CompatiblePython
}
if (-not $sel) {
    Write-Host "Impossible d'obtenir Python 3.12 automatiquement." -ForegroundColor Red
    Write-Host "Installe-le manuellement : https://www.python.org/downloads/release/python-3127/ puis relance." -ForegroundColor Yellow
    exit 1
}
Write-Host "== Python selectionne : py $sel ==" -ForegroundColor Cyan

if (Test-Path .\.venv) {
    Write-Host "Suppression de l'ancien .venv…" -ForegroundColor Yellow
    Remove-Item -Recurse -Force .\.venv
}

Write-Host "== Creation du venv (.venv) ==" -ForegroundColor Cyan
& py $sel -m venv .venv

$venvPy = ".\.venv\Scripts\python.exe"
Write-Host "== pip + setuptools + wheel ==" -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip setuptools wheel

Write-Host "== Installation des dependances ==" -ForegroundColor Cyan
& $venvPy -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "webrtcvad a echoue -> bascule sur webrtcvad-wheels" -ForegroundColor Yellow
    & $venvPy -m pip install webrtcvad-wheels
    & $venvPy -m pip install -r requirements.txt
}

Write-Host "`n== Verification ==" -ForegroundColor Cyan
& $venvPy -c "import pkg_resources, streamlit, webrtcvad, faster_whisper, rapidfuzz; print('Toutes les dependances cles sont importables.')"

Write-Host "`nOK. Lancer : .\run.ps1   (ou)   .\.venv\Scripts\python.exe -m streamlit run app/main.py" -ForegroundColor Green
Write-Host "Pense a Ollama : https://ollama.com  puis  ollama pull gemma3:4b"
