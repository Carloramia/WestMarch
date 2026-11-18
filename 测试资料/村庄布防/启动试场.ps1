$ErrorActionPreference = 'Stop'
$trialUrl = 'http://127.0.0.1:8877/'
try { $trialResponse = Invoke-WebRequest -Uri $trialUrl -UseBasicParsing -TimeoutSec 2 } catch {
    $trialPython = (Get-Command python -ErrorAction Stop).Source
    Start-Process -FilePath $trialPython -ArgumentList @('"' + (Join-Path $PSScriptRoot 'server.py') + '"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
    Start-Sleep -Seconds 2
}
Start-Process $trialUrl
