# Changelog

## v0.4.6-beta — Windows installer and updates (testing candidate)

- Add an interactive Inno Setup Windows installer with port, Private-LAN firewall, TMDB opt-in, VPN-only remote admin, beta update channel and shortcut options.
- Add upgrade-in-place for the existing service without data migration; timestamped pre-upgrade backups and preserved ProgramData.
- Add installer-managed firewall rule cleanup on upgrade and removal.
- Add explicit user-initiated release checks and SHA-256 verification for download-and-install.
- Windows installer compilation/service-upgrade smoke test pending; no production release has been tagged.

## Unreleased — v0.4.5-beta (Windows service / remote-admin prototype)

- Package Windows EXE locally using PyInstaller and configure an Automatic (Delayed Start) WinSW service under LocalService.
- Separate runtime credentials and SQLite data from packaged static assets and application executable.
- Add explicit VPN address allowlist, separate administrator password, and one-hour admin sessions for optional remote administration.
- Keep gallery-only access for ordinary LAN clients; remote administration is disabled until configured.
- Add Windows build, migration, service-install, uninstall, backup, and rollback instructions.
- Windows executable/service installation remains **untested on Windows** pending host validation.

## v0.4.4-beta — Security hardening (LAN-only)

- Require JSON content type and reject cross-site browser POSTs.
- Prevent internal server exception details from being sent to browsers.
- Expire TMDB actor portraits and stale provider result records after 180 days.
- Keep TMDB/Wikimedia disabled by default and prevent portrait redirects to untrusted hosts.
- Development-only release; production interoperability and provider compliance remain unverified.

## Unreleased — noncommercial license adopted

- Adopted a custom noncommercial, network-source-sharing license and plain-language usage guide.
- Added unadopted contributor-rights template and limitations checklist to protect independent contributors and commercial permission rights.
- Updated community and release documentation; this is a source-documentation update; paid legal review is not required.


## Unreleased — Public source preparation

- Restructure installation, contributor, privacy, support, security, and architecture documentation.
- Add GitHub issue/PR templates, code ownership, and least-privilege CI settings.
- Add TMDB text attribution to app footer; approved provider logo remains pending.
- No change to library indexing or artwork matching behavior.

## v0.4.2 — Faster single-result portrait approval

- Automatically apply qualifying sole artwork matches with corroborating name and production credit, provided no contradictory evidence or provider failure exists.
- Add background batch acceptance for eligible existing queued single-candidate reviews.
- Offer one-click approval on eligible review cards.

## v0.4.1 — Portrait verification

- Display full-size portrait candidate alongside Plex filmography and matching provider credits.
- Add role-conflict safeguards, candidate-specific rejection and explicit verification before approval.

## v0.4.0 — Credit-aware enrichment

- Scan missing artwork using configured external providers and corroborate movie/show credits.
- Store background scan progress and review decisions; support pause/resume.

## v0.3.0 — Network-aware links and artwork sources

- Choose local Plex links for LAN visitors, app.plex.tv links for other visitors.
- Add configurable artwork providers, manual portrait override and missing-portrait filtering.

## v0.2.2 — Local Plex links

- Link titles to direct Plex Web on LAN instead of the hosted Plex site.

## v0.2.1 — Search hotfix

- Correct duplicate search cards caused by stale asynchronous results.

## v0.2.0 — LAN hosting

- Enable LAN hosting, password protection, background indexing and Windows startup support.

## v0.1.0 — Initial prototype

- Add cross-library cast indexing and searchable gallery.
