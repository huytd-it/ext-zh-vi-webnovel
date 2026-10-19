$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
if (Get-NetTCPConnection -LocalPort 17865 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Port 17865 already used; will not touch the existing service.'
}
$temp = Join-Path 'C:/Users/huytd/AppData/Local/Temp/opencode' ('novel-api-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
$start = [System.Diagnostics.ProcessStartInfo]::new()
$start.FileName = Join-Path $root 'dist/NovelLocal/NovelLocal.exe'
$start.Arguments = '--serve'
$start.UseShellExecute = $false
$start.Environment['PATH'] = 'C:\Windows\System32;C:\Windows'
$start.Environment['NOVEL_LOCAL_DATA'] = $temp
$token = 'frozen-smoke-token-not-a-user-credential'
$start.Environment['NOVEL_LOCAL_TOKEN'] = $token
$start.Environment.Remove('PYTHONHOME') | Out-Null
$start.Environment.Remove('PYTHONPATH') | Out-Null
$process = [System.Diagnostics.Process]::Start($start)
try {
    $response = $null
    for ($n=0; $n -lt 100; $n++) {
        if ($process.HasExited) { throw 'Frozen server exited before startup.' }
        try {
            $response = Invoke-WebRequest 'http://127.0.0.1:17865/v1/health' -UseBasicParsing -TimeoutSec 1 -Headers @{Authorization="Bearer $token"}
            break
        } catch { Start-Sleep -Milliseconds 100 }
    }
    if (!$response -or $response.StatusCode -ne 200) { throw 'Frozen service did not answer health.' }
    $listener = Get-NetTCPConnection -LocalPort 17865 -State Listen
    if ($listener.LocalAddress -ne '127.0.0.1' -or $listener.OwningProcess -ne $process.Id) {
        throw 'Unexpected listener address or process.'
    }
    $unauthorized = $false
    try { Invoke-WebRequest 'http://127.0.0.1:17865/v1/health' -UseBasicParsing -TimeoutSec 2 | Out-Null }
    catch { $unauthorized = [int]$_.Exception.Response.StatusCode -eq 401 }
    if (!$unauthorized) { throw 'Missing token was not rejected.' }
    @{result='passed'; loopback='127.0.0.1'; missing_token=401; health=($response.Content | ConvertFrom-Json)} |
        ConvertTo-Json -Depth 8 | Set-Content (Join-Path $temp 'api-report.json') -Encoding UTF8
    Get-Content (Join-Path $temp 'api-report.json') -Encoding UTF8
} finally {
    if (!$process.HasExited) { $process.Kill(); $process.WaitForExit() }
}
