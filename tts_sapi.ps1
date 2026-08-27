param(
    [Parameter(Mandatory = $true)][string]$TextFile,
    [Parameter(Mandatory = $true)][string]$OutputPath,
    [string]$Language = "Mandarin Chinese",
    [int]$Rate = 0
)

$ErrorActionPreference = "Stop"
$text = [System.IO.File]::ReadAllText($TextFile, [System.Text.Encoding]::UTF8)
if ([string]::IsNullOrWhiteSpace($text)) { throw "TTS text is empty" }

$voice = New-Object -ComObject SAPI.SpVoice
$stream = New-Object -ComObject SAPI.SpFileStream
$format = New-Object -ComObject SAPI.SpAudioFormat
try {
    $tokens = $voice.GetVoices()
    $descriptions = @()
    for ($index = 0; $index -lt $tokens.Count; $index++) {
        $token = $tokens.Item($index)
        $description = $token.GetDescription()
        $descriptions += $description
        if ($Language -match "Mandarin|Chinese|普通|国语|國語" -and
            $description -match "Huihui|Yaoyao|Kangkang|Hanhan|Chinese|Mandarin|中文") {
            $voice.Voice = $token
            break
        }
    }
    try { $voice.Rate = [Math]::Max(-10, [Math]::Min(10, $Rate)) } catch { throw "SAPI rate failed: $($_.Exception.Message)" }
    try { $voice.Volume = 100 } catch { throw "SAPI volume failed: $($_.Exception.Message)" }
    $format.Type = 18
    $stream.Format = $format
    try { $stream.Open($OutputPath, 3, $false) } catch { throw "SAPI output open failed: $($_.Exception.Message)" }
    try { $voice.AudioOutputStream = $stream } catch { throw "SAPI stream binding failed: $($_.Exception.Message)" }
    try { [void]$voice.Speak($text, 0) } catch { throw "SAPI speak failed: $($_.Exception.Message). Installed voices: $($descriptions -join ', ')" }
    try { $stream.Close() } catch { throw "SAPI output close failed: $($_.Exception.Message)" }
}
finally {
    try { $stream.Close() } catch {}
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($format)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($stream)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice)
}
