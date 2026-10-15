# Architecture

Plex Cast Explorer is a small Python standard-library HTTP application with a static HTML/CSS/JavaScript frontend.

```text
Browser on LAN → Cast Explorer HTTP (:8765) → SQLite index and local portrait cache
                          │
                          ├→ Plex Media Server (:32400; token in server-side config)
                          └→ Optional provider APIs (TMDB, ThePornDB, Wikimedia)
```

- **`app.py`**: HTTP routes, authentication, Plex indexing, SQLite queries, artwork lookups, matching, and background tasks.
- **`static/`**: user interface; no client-side Plex/API secrets.
- **`BUILD-INSTALLER.cmd`** and **`build_installer_windows.ps1`**: supported local Windows build pipeline; `installer/` holds service/updater utilities.
- **`test_app.py`**: synthetic indexing, matching, and route tests.
- **`*.json` / SQLite / `portraits/`** (runtime): per-installation credentials, settings, index, queue, and downloaded media; excluded from Git.

## Authentication and boundaries

LAN viewing requires a gallery password and signed cookie. Localhost traffic bypasses the gallery login and can administer the app; this is not a complete multi-user role model. A reverse proxy terminating connections on loopback can defeat the admin boundary; do not expose this app publicly or forward untrusted clients to loopback.

## Data updates

The app uses scheduled incremental Plex sync and optional background enrichment. SQLite holds the combined library index, cached review decisions, and override references. Refresh jobs and image downloads are I/O-bound; large libraries can take significant time. A request for a performer does not modify Plex.
