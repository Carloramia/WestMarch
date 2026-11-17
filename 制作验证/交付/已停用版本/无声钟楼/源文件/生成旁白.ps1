$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$lines = Get-Content -LiteralPath (Join-Path $PSScriptRoot '旁白.json') -Raw -Encoding utf8 | ConvertFrom-Json
$speaker = New-Object -ComObject SAPI.SpVoice
$speaker.Voice = $speaker.GetVoices() | Where-Object { $_.GetDescription() -like '*Huihui*' } | Select-Object -First 1
$speaker.Rate = 1
$speaker.Volume = 100
for ($i=0; $i -lt $lines.Count; $i++) {
    $stream = New-Object -ComObject SAPI.SpFileStream
    $stream.Format.Type = 22
    $stream.Open((Join-Path $root ('音频\voice_{0:d2}.wav' -f $i)), 3, $false)
    $speaker.AudioOutputStream = $stream
    $null = $speaker.Speak([string]$lines[$i][2])
    $stream.Close()
}
Write-Output ('Generated {0} narration clips.' -f $lines.Count)
