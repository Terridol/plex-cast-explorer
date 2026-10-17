# Troubleshooting

**The page works locally but not on another PC.** Confirm the server is listening on `0.0.0.0:8765` (Windows: `netstat -ano | findstr :8765`). From the other PC, try `Test-NetConnection <SERVER-IP> -Port 8765`. Check the Windows network profile, inbound firewall rule, and any UniFi VLAN isolation. No WAN port-forwarding is needed.

**I cannot find Settings.** Administration is available on the host through `http://127.0.0.1:8765`. A remote browser receives gallery-only access unless its actual client IP is on the explicitly configured VPN admin allowlist and the user has completed both the gallery and separate admin logins. Never forward the port from the public Internet.

**Plex asks for a PIN after opening a title.** Plex Web manages its own browser session and PIN, independent of Cast Explorer. Open local Plex directly, sign in, and configure Plex's own auto-sign-in behavior on trusted browsers only.

**Plex actors have names but no photographs after sync.** Sync now fetches and caches any `Role.thumb` URLs that Plex returns, including for previously indexed movies/shows. Run Sync again to backfill the local `plex-portraits/` cache. If a Role has no `thumb`, but exposes a valid Plex person `Role.key` or `Role.ratingKey`, Plex Cast Explorer will also check that person's Plex metadata for a portrait. Custom metadata agents may provide `metadata://` or `media://` image references, which are accessed through the authenticated Plex metadata-file endpoint. If neither the Role nor the Plex person record exposes an image, use TMDB/TPDB enrichment or add artwork to Plex. Run a **full metadata sync** once when upgrading an existing database if you need to discover previously unindexed person keys; subsequent incremental syncs backfill cached images. Cast images from custom metadata agents (e.g., THDB) are supported when Plex exposes the image in `Role.thumb` or a linked Plex person record: Plex Cast Explorer retrieves Plex-relative images directly and attempts to retrieve public HTTPS custom-scraper URLs through Plex's authenticated `/photo/:/transcode` endpoint. Plex images from private/LAN addresses or unsupported URL schemes are deliberately not proxied (the underlying Plex server may reject them too). For a privately hosted scraper, configure the scraper so Plex supplies a working local Plex image reference or an accessible public HTTPS portrait URL. The app never accepts arbitrary browser-entered image-proxy URLs. If the Plex artwork host is unreachable, Sync finishes with warnings and retries the missing thumbnails on your next Sync. Ensure the server can reach Plex's artwork hosts and that LocalService can write to `C:\ProgramData\PlexCastExplorer\plex-portraits`. A user-approved artwork override is never replaced by this cache. If you see many HTTP 403 failures from *Plex CDN*, Cast Explorer also attempts a safe Plex photo-transcoder fallback for those trusted hosts. When direct and Plex-mediated requests both fail, investigate image-host access and upstream metadata availability; some Plex Media Server 1.43.5 installations have reported 403 on `metadata-static.plex.tv` images (https://forums.plex.tv/t/fetch-failed-with-code-403/944432). This is a diagnostic lead, not proof of your particular root cause.

**Portrait caching shows an HTTP error.** The sync banner now reports the numeric status, a safe source category (**Plex internal**, **Plex server**, **Plex CDN**, or **custom scraper**), and updates failures while the scan is running. This identifies which image retrieval path failed without exposing private URLs. HTTP **404/410** indicates the image reference is unavailable on Plex and is counted as *missing* rather than a fatal sync error. HTTP **401/403** indicates Plex denied the image request (inspect Plex token and agent/image access). HTTP **429** indicates rate limiting; wait before retrying. HTTP **500–599** indicates an upstream/server issue. For repeated HTTP 401/403 or server 5xx responses from **one image origin**, that origin is paused only after a representative sample from across its entire list fails without any successful portrait downloads; the scan continues downloading portraits from other origins, including independent Plex CDNs and custom agents. For HTTP 429, the entire image pass pauses because rate limiting can affect the server globally. A paused origin's remaining images are counted as *skipped* (not downloaded, not attempted); the progress number counts actual attempts. Images from skipped sources can be retried on a later sync after checking provider availability. Already downloaded portraits remain cached and later syncs retry failures. The UI shows **portraits** rather than titles during artwork caching. Logs intentionally do not contain full artwork URLs or Plex access tokens.

**An actor portrait is missing or wrong.** Check the performer and associated Plex credits, try optional provider search, and review the image source. One matching production does not prove a person's identity. You can reject candidates or remove overrides.

**Provider lookups fail.** Verify provider credentials, HTTP errors, API quotas and DNS. Pause enrichment during outages; use Retry failed lookups afterward.

**New version doesn't appear.** Pull `dev` through GitHub Desktop, run `BUILD-INSTALLER.cmd`, and run the resulting uniquely named Setup EXE as Administrator. Setup stops and restarts the Windows service, retains `ProgramData`, and checks the HTTP version before Finish. If Setup fails, inspect `C:\ProgramData\PlexCastExplorer\logs\installer-last-error.txt` and the service wrapper log; do not delete your database or credentials.

## Artwork enrichment reports “Unterminated string” at byte 1,000,000

Older builds read only 1,000,001 bytes of provider JSON, which could truncate large ThePornDB scene-credit responses. The 1.0 release candidate now allows bounded complete JSON responses up to **8 MiB**, with a clear size error for larger responses. Pull and build the updated release candidate, then **pause the enrichment run** before selecting **Retry failed lookups** and **Start / resume enrichment**. Retrying clears only saved error records; previously accepted portraits and unmatched results are retained. If the provider still exceeds 8 MiB, inspect the warning and report it without exposing API tokens or private Plex metadata. Do not disable provider response bounds.

## Export indexing and portrait matching diagnostics

On the Plex Cast Explorer server, open `http://127.0.0.1:8765/api/diagnostics/export`
(replace 8765 if you changed the port). This downloads a read-only JSON snapshot
of current indexing/enrichment state, match outcomes by source, pending totals,
and up to 500 representative review/error/unmatched records. It is limited to
server-local or authenticated authorized remote administrators. No tokens, image
URLs or raw provider error messages are included, but performer names are present:
review the export before sharing it outside your deployment. The original
database and live scans are not altered. A download does not pause either scan.

For a stalled scan, export once, wait a few minutes, then export again. Compare
`index.current`, `index.phase`, `enrichment.checked`, and `enrichment.running`
to identify which pipeline is stalled. The export is a diagnostic sample rather
than the complete actor catalog.
