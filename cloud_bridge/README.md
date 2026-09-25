# Cloud → local Ableton bridge

Lets a claude.ai/code cloud session call MCP tools on your Windows PC via a
Cloudflare quick tunnel and a claude.ai custom connector. OSC stays on localhost.

## Run
1. Open Ableton, set Control Surface = AbletonOSC.
2. PowerShell: `cd <repo>\cloud_bridge; .\start.ps1`
   (first run may need `Set-ExecutionPolicy -Scope Process Bypass`).
3. claude.ai → Settings → Connectors → Add custom connector
   - Name: `ableton-ping`, URL: paste from clipboard.
4. claude.ai/code → new session → enable `ableton-ping` from `+` →
   "Call ping with bpm 123". Success = Ableton tempo reads 123.
5. Done: press Enter in the PowerShell window, delete the connector.

A new secret and a new tunnel URL are generated every run, so the connector must
be re-added each time. That is intentional: a stale URL is a dead URL.

## Known failure modes → fallback
| Symptom | Likely cause |
|---|---|
| Tools don't appear in session | Connector not enabled in `+`, or cloud sessions don't surface custom connectors on your plan |
| 421 / host errors | `--http-host-header localhost:8000` missing |
| Session stalls | Tool approval prompt waiting; approve promptly |

If any persist: use Remote Control for live DAW work.

## Security
Only auth is the secret URL path. Never paste the full URL into chats, commits,
or screenshots. `ping` only sets tempo (clamped 20–999); review any new tool
before exposing it here.

## Scope
This controls Ableton via AbletonOSC. Serum has no network surface; reaching
Serum parameters needs Ableton device-parameter OSC calls on the track hosting
Serum — not implemented yet.
