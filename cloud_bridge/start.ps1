# Starts the MCP server and a Cloudflare quick tunnel, then prints the connector URL.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install "mcp[cli]" python-osc
}

if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
    winget install --id Cloudflare.cloudflared
    Write-Host "cloudflared installed. Open a new PowerShell window and re-run start.ps1."
    exit 1
}

$env:MCP_BRIDGE_SECRET = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(24))"

$server = Start-Process .\.venv\Scripts\python.exe -ArgumentList "server.py" -PassThru -NoNewWindow
$log = Join-Path $env:TEMP "cloudflared-bridge.log"
Remove-Item $log -ErrorAction SilentlyContinue
$tunnel = Start-Process cloudflared -ArgumentList "tunnel --url http://localhost:8000 --http-host-header localhost:8000" `
    -RedirectStandardError $log -PassThru -NoNewWindow

$url = $null
for ($i = 0; $i -lt 30 -and -not $url; $i++) {
    Start-Sleep 1
    if (Test-Path $log) {
        $m = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" | Select-Object -First 1
        if ($m) { $url = $m.Matches[0].Value }
    }
}
if (-not $url) { Write-Host "Tunnel URL not found; see $log"; $server | Stop-Process; $tunnel | Stop-Process; exit 1 }

$connector = "$url/mcp-$env:MCP_BRIDGE_SECRET"
Set-Clipboard $connector
Write-Host "`nConnector URL (copied to clipboard):`n$connector`n"
Write-Host "Press Enter to stop the server and tunnel."
Read-Host | Out-Null
$tunnel | Stop-Process -ErrorAction SilentlyContinue
$server | Stop-Process -ErrorAction SilentlyContinue
Write-Host "Stopped. Delete the connector on claude.ai - this secret is now dead."
