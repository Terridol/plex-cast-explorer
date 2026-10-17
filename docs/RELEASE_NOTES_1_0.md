# Plex Cast Explorer 1.0 — Draft release notes

**Unpublished 1.0.0 release notes; do not distribute as a GA announcement until acceptance gates pass.**

Plex Cast Explorer is a self-hosted Windows cast explorer for Plex movie/TV libraries, with actor credits, searchable filmographies, portraits and optional reviewed artwork.

## Features in the frozen 1.0 scope

- Windows x64 single installer and automatic WinSW service under `LocalService`, with optional Private-profile Windows Firewall rule.
- Gallery authentication plus separate, VPN-allowlisted remote administration with a distinct administrator password.
- Incremental Plex indexing, actor search and filters, detail/credit pages, portrait overrides, TMDB-first/TPDB-fallback matching, and the ability to rescan previously unmatched performers without losing applied portraits.
- In-place upgrade designed to preserve `C:\ProgramData\PlexCastExplorer` (SQLite index, configuration, credentials, artwork and backups).

## Security and licensing boundaries

The built-in web server serves **HTTP only**: trusted LAN/private VPN, never public WAN forwarding. This project uses a custom noncommercial source-share license, **not** an OSI-approved open-source license. Provider content/images/trademarks have separate rights. Authorized TMDB lookups are available as the preferred external portrait provider, with an installer opt-in, user-supplied API token, official TMDB logo and required non-endorsement notice. ThePornDB is queried as a fallback only when TMDB has no matching portrait. Wikimedia remains disabled. Users must comply with the provider's actual API and media-use terms. Existing user artwork is not erased by upgrading. The public release installer must be checked for its final signature state; an unsigned installer must be clearly labeled as such.

## Upgrade and support

Back up `C:\ProgramData\PlexCastExplorer` before upgrades. Do not uninstall an existing service before in-place Setup. On a failed service configuration, inspect `C:\ProgramData\PlexCastExplorer\logs\installer-error-details.log` and [Windows installation instructions](WINDOWS_INSTALLER.md).

The release acceptance and publication conditions are in [the 1.0 checklist](RELEASE_CHECKLIST.md). Do not publish these notes as stable until they have been met.
