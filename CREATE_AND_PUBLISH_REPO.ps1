param([string]$ProjectRoot=(Get-Location).Path,[string]$Repository="HistoMetPath-Web")
$ErrorActionPreference="Stop"
Set-Location -LiteralPath $ProjectRoot
if(Test-Path .git){throw "This folder is already a Git repository."}
py -3.11 -m venv .venv
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest -q
if($LASTEXITCODE -ne 0){throw "Tests failed."}
python -m compileall app.py pages histometpath_web
if($LASTEXITCODE -ne 0){throw "Compilation failed."}
git init -b main
git add .
git commit -m "Launch HistoMetPath Web v0.1"
gh repo create $Repository --public --source . --remote origin --push --description "Interactive synthetic-only Streamlit companion to HistoMetPath"
if($LASTEXITCODE -ne 0){throw "GitHub repository creation failed."}
Write-Host "PASS: Repository created and pushed." -ForegroundColor Green
Write-Host "NEXT: Deploy app.py from main at https://share.streamlit.io" -ForegroundColor Cyan
