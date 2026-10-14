# Troubleshooting

**The page works locally but not on another PC.** Confirm the server is listening on `0.0.0.0:8765` (Windows: `netstat -ano | findstr :8765`). From the other PC, try `Test-NetConnection <SERVER-IP> -Port 8765`. Check the Windows network profile, inbound firewall rule, and any UniFi VLAN isolation. No WAN port-forwarding is needed.

**I cannot find Settings.** Administration is intentionally available only when opening `http://127.0.0.1:8765` **on the host running Cast Explorer**. Browsers on other PCs are gallery-only.

**Plex asks for a PIN after opening a title.** Plex Web manages its own browser session and PIN, independent of Cast Explorer. Open local Plex directly, sign in, and configure Plex's own auto-sign-in behavior on trusted browsers only.

**An actor portrait is missing or wrong.** Check the performer and associated Plex credits, try optional provider search, and review the image source. One matching production does not prove a person's identity. You can reject candidates or remove overrides.

**Provider lookups fail.** Verify provider credentials, HTTP errors, API quotas and DNS. Pause enrichment during outages; use Retry failed lookups afterward.

**New version doesn't appear.** Stop all running Cast Explorer processes, replace only source files, restart, and hard refresh the browser (`Ctrl+F5`). Keep your local `*.json`, database, and `portraits/` files.
