$ErrorActionPreference = "Stop"
Set-Location "D:\HistoMetPath-Web\HistoMetPath-Web"
$env:HISTOMETPATH_MODEL_PATH = (Resolve-Path ".\local_model_artifacts\histometpath_resnet18_patch_state_dict.pt").Path
$env:HISTOMETPATH_POSITIVE_PNG = "$HOME\Downloads\HistoMetPath_png_equivalence\known_positive_index_0.png"
$env:HISTOMETPATH_NEGATIVE_PNG = "$HOME\Downloads\HistoMetPath_png_equivalence\known_negative_index_6.png"
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Prototype tests failed." }
python -m py_compile ".\histometpath_web\inference.py" ".\pages\2_Upload_and_Analyze.py"
if ($LASTEXITCODE -ne 0) { throw "Prototype compilation failed." }
Write-Host "PASS: Local Upload & Analyze prototype tests and exact score checks passed." -ForegroundColor Green

