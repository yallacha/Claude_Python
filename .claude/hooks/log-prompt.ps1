param([Parameter(Mandatory = $true)][ValidateSet('prompt', 'response')][string]$Mode)

$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$utf8 = New-Object System.Text.UTF8Encoding($false)

$raw = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($raw)) { exit 0 }
$data = $raw | ConvertFrom-Json

$projectDir = $env:CLAUDE_PROJECT_DIR
if (-not $projectDir) { $projectDir = $data.cwd }
if (-not $projectDir) { $projectDir = (Get-Location).Path }
$logFile = Join-Path $projectDir 'prompt.md'
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

function Get-LastAssistantText($transcriptPath) {
    if (-not $transcriptPath -or -not (Test-Path -LiteralPath $transcriptPath)) { return $null }
    $lines = [System.IO.File]::ReadAllLines($transcriptPath, [System.Text.Encoding]::UTF8)
    $texts = New-Object System.Collections.Generic.List[string]
    for ($i = $lines.Length - 1; $i -ge 0; $i--) {
        if ([string]::IsNullOrWhiteSpace($lines[$i])) { continue }
        try { $entry = $lines[$i] | ConvertFrom-Json } catch { continue }
        if ($entry.isSidechain) { continue }
        $content = $entry.message.content
        if ($entry.type -eq 'user') {
            # A real user prompt (not a tool_result) marks the start of this turn
            $isToolResult = $false
            if ($content -isnot [string]) {
                foreach ($c in @($content)) { if ($c.type -eq 'tool_result') { $isToolResult = $true } }
            }
            if (-not $isToolResult -and -not $entry.isMeta) { break }
        }
        elseif ($entry.type -eq 'assistant') {
            $parts = @()
            if ($content -is [string]) { $parts += $content }
            else { foreach ($c in @($content)) { if ($c.type -eq 'text' -and $c.text) { $parts += $c.text } } }
            if ($parts.Count -gt 0) { $texts.Insert(0, ($parts -join "`n")) }
        }
    }
    if ($texts.Count -eq 0) { return $null }
    return ($texts -join "`n`n")
}

if ($Mode -eq 'prompt') {
    $text = $data.prompt
    if (-not $text) { exit 0 }
    $block = "`r`n---`r`n`r`n## Prompt ($stamp)`r`n`r`n$text`r`n"
}
else {
    $text = $data.last_assistant_message
    if (-not $text) { $text = Get-LastAssistantText $data.transcript_path }
    if (-not $text) { exit 0 }
    $block = "`r`n## Response ($stamp)`r`n`r`n$text`r`n"
}

[System.IO.File]::AppendAllText($logFile, $block, $utf8)
exit 0
