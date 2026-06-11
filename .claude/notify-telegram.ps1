# Stop-hook: notify the owner in Telegram that Claude Code finished.
# Token and owner_id are read from ../.env (no secret in settings.json).
# Errors are swallowed so the hook never blocks session end.
#
# IMPORTANT: keep this file pure ASCII. Windows PowerShell 5.1 reads a .ps1
# without BOM as ANSI (CP1251 here), which corrupts any non-ASCII literal.
# The emoji is built from a code point at runtime to avoid that trap.
$ErrorActionPreference = 'Stop'
try {
    $envPath = Join-Path $PSScriptRoot '..\.env'
    if (-not (Test-Path $envPath)) { exit 0 }

    $token = $null
    $owner = $null
    foreach ($line in Get-Content $envPath -Encoding UTF8) {
        if ($line -match '^\s*BOT_TOKEN\s*=\s*(.+?)\s*$') { $token = $Matches[1] }
        elseif ($line -match '^\s*OWNER_ID\s*=\s*(.+?)\s*$') { $owner = $Matches[1] }
    }
    if ([string]::IsNullOrWhiteSpace($token) -or [string]::IsNullOrWhiteSpace($owner)) { exit 0 }

    Add-Type -AssemblyName System.Web
    $check = [char]0x2705   # white heavy check mark
    $ts = Get-Date -Format 'HH:mm:ss'
    $text = "$check Claude Code finished a turn in SiriusTG_Bot ($ts)"
    $encText = [System.Web.HttpUtility]::UrlEncode($text)
    $uri = "https://api.telegram.org/bot$token/sendMessage?chat_id=$owner&text=$encText"

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-RestMethod -Method Post -Uri $uri -TimeoutSec 15 | Out-Null
} catch {
    # silent
}
exit 0
