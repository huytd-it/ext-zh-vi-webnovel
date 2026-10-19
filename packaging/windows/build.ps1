$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../..')
npm ci --legacy-peer-deps
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
npm run build
if ($LASTEXITCODE -ne 0) { throw 'Extension build failed' }
& .venv/Scripts/python.exe -m PyInstaller packaging/windows/novel-local.spec --noconfirm
if ($LASTEXITCODE -ne 0) { throw 'Runtime build failed' }
& .venv/Scripts/python.exe scripts/licenses.py --fetch-missing
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
New-Item -ItemType Directory -Path artifacts -Force | Out-Null
Compress-Archive -Path dist/extension -DestinationPath artifacts/NovelLocal-extension-0.1.0.zip -Force
$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (!$iscc) {
    $candidate = 'C:/Program Files (x86)/Inno Setup 6/ISCC.exe'
    if (Test-Path $candidate) { $iscc = Get-Item $candidate }
}
if (!$iscc) { throw 'Thiếu Inno Setup 6. Runtime/extension đã build; chưa tạo được bộ cài.' }
& $iscc.FullName packaging/windows/installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed' }
