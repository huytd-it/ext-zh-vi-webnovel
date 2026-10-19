$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$folder = 'novel-ki' + [char]0x1EC3 + 'm th' + [char]0x1EED + '-' + [guid]::NewGuid().ToString('N')
$temp = Join-Path 'C:/Users/huytd/AppData/Local/Temp/opencode' $folder
New-Item -ItemType Directory -Path $temp | Out-Null
Copy-Item (Join-Path $root 'dist/NovelLocal') (Join-Path $temp 'runtime') -Recurse
$report = Join-Path $temp 'diagnostic.json'
$start = [System.Diagnostics.ProcessStartInfo]::new()
$start.FileName = Join-Path $temp 'runtime/NovelLocal.exe'
$start.ArgumentList.Add('--diagnose')
$start.ArgumentList.Add('--diagnostic-output')
$start.ArgumentList.Add($report)
$start.UseShellExecute = $false
$start.Environment['PATH'] = 'C:\Windows\System32;C:\Windows'
$start.Environment.Remove('PYTHONHOME') | Out-Null
$start.Environment.Remove('PYTHONPATH') | Out-Null
$process = [System.Diagnostics.Process]::Start($start)
if (!$process.WaitForExit(20000)) {
    $process.Kill()
    throw 'Packaged diagnostic timed out; only test-created process was stopped.'
}
if ($process.ExitCode -ne 0 -or !(Test-Path $report)) { throw 'Packaged diagnostic failed.' }
Get-Content $report -Raw -Encoding UTF8
Write-Output "Evidence: $report"
