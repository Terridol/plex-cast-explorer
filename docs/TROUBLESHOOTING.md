# Troubleshooting

**The page works locally but not on another PC.** Confirm the server is listening on `0.0.0.0:8765` (Windows: `netstat -ano | findstr :8765`). From the other PC, try `Test-NetConnection <SERVER-IP> -Port 8765`. Check the Windows network profile, inbound firewall rule, and any UniFi VLAN isolation. No WAN port-forwarding is needed.

**I cannot find Settings.** Administration is available on the host through `http://127.0.0.1:8765`. A remote browser receives gallery-only access unless its actual client IP is on the explicitly configured VPN admin allowlist and the user has completed both the gallery and separate admin logins. Never forward the port from the public Internet.

**Plex asks for a PIN after opening a title.** Plex Web manages its own browser session and PIN, independent of Cast Explorer. Open local Plex directly, sign in, and configure Plex's own auto-sign-in behavior on trusted browsers only.

**An actor portrait is missing or wrong.** Check the performer and associated Plex credits, try optional provider search, and review the image source. One matching production does not prove a person's identity. You can reject candidates or remove overrides.

**Provider lookups fail.** Verify provider credentials, HTTP errors, API quotas and DNS. Pause enrichment during outages; use Retry failed lookups afterward.

**New version doesn't appear.** Pull `dev` through GitHub Desktop, run `BUILD-INSTALLER.cmd`, and run the resulting uniquely named Setup EXE as Administrator. Setup stops and restarts the Windows service, retains `ProgramData`, and checks the HTTP version before Finish. If Setup fails, inspect `C:\ProgramData\PlexCastExplorer\logs\installer-last-error.txt` and the service wrapper log; do not delete your database or credentials.
