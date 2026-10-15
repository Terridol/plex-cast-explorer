# Plex Cast Explorer 1.0 — Draft release notes

**Unpublished 1.0.0 release notes; do not distribute as a GA announcement until acceptance gates pass.**

Plex Cast Explorer is a self-hosted Windows cast explorer for Plex movie/TV libraries, with actor credits, searchable filmographies, portraits and optional reviewed artwork.

## Features in the frozen 1.0 scope

- Windows x64 single installer and automatic WinSW service under `LocalService`, with optional Private-profile Windows Firewall rule.
- Gallery authentication plus separate, VPN-allowlisted remote administration with a distinct administrator password.
- Incremental Plex indexing, actor search and filters, detail/credit pages, portrait overrides and selective verified provider matching.
- In-place upgrade designed to preserve `C:\ProgramData\PlexCastExplorer` (SQLite index, configuration, credentials, artwork and backups).

## Security and licensing boundaries

The built-in web server serves **HTTP only**: trusted LAN/private VPN, never public WAN forwarding. This project uses a custom noncommercial source-share license, **not** an OSI-approved open-source license. Provider content/images/trademarks have separate rights. TMDB and Wikimedia lookups are **unavailable** in v1.0 due to unresolved API/attribution rights; old opt-in flags do not reactivate them. Existing user artwork is not erased by upgrading. The public release installer must be checked for its final signature state; an unsigned installer must be clearly labeled as such.

## Upgrade and support

Back up `C:\ProgramData\PlexCastExplorer` before upgrades. Do not uninstall an existing service before in-place Setup. On a failed service configuration, inspect `C:\ProgramData\PlexCastExplorer\logs\installer-error-details.log` and [Windows installation instructions](WINDOWS_INSTALLER.md).

The release acceptance and publication conditions are in [the 1.0 checklist](RELEASE_CHECKLIST.md). Do not publish these notes as stable until they have been met.
