$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../..')
$inventoryPath = 'dist/NovelLocal/THIRD_PARTY_LICENSES/inventory.json'
if (!(Test-Path $inventoryPath)) { throw 'Collect runtime license texts before packaging.' }
$inventory = Get-Content $inventoryPath -Raw -Encoding UTF8 | ConvertFrom-Json
if (@($inventory | Where-Object { $_.files.Count -eq 0 }).Count -gt 0) {
    throw 'Missing runtime license texts; review inventory before packaging.'
}
New-Item -ItemType Directory -Path artifacts -Force | Out-Null
Compress-Archive -Path dist/extension -DestinationPath artifacts/NovelLocal-extension-0.1.0.zip -Force
Compress-Archive -Path dist/NovelLocal,dist/extension,docs,README.md -DestinationPath artifacts/NovelLocal-0.1.0-Windows-x64-preview.zip -Force
Get-FileHash artifacts/*.zip -Algorithm SHA256 | Select-Object Path,Hash | ConvertTo-Json | Set-Content artifacts/checksums.json -Encoding UTF8
Get-Item artifacts/*.zip | Select-Object Name,Length
