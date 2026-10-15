# Plex Cast Explorer

Self-hosted Plex cast browser for Windows. Index actors across movie and TV libraries, browse portraits and credits, and optionally search external portrait providers.

**Version:** `1.0.0` (release source; GA installer not yet verified/published) · **Windows:** 10/11 x64 · **Runtime:** bundled into installer · **Source build:** Python 3.10+ and Inno Setup 6

**Project state:** Feature-frozen 1.0 release source, **not yet a published or verified general release**. See [the release checklist](docs/RELEASE_CHECKLIST.md) before promoting or distributing a stable installer.

## Install and use

1. On a Windows build machine, clone `Terridol/plex-cast-explorer` with GitHub Desktop and select the **`dev`** branch.
2. Choose **Fetch origin → Pull origin**, then run **`BUILD-INSTALLER.cmd`** in the repository directory.
3. The local build validates PowerShell syntax before any other step, runs Python regression/negative tests, builds a self-contained application, smoke-tests that executable with disposable data, compiles Inno Setup, and verifies the installer/checksum.
4. The uniquely named installer is placed in `output/`: for example, `PlexCastExplorer-Setup-1.0.0-dev-20261014-203512123-g23a496e7-win-x64.exe`. **Every new installer compilation first deletes all previous files and subdirectories in `output/`** (including old setup files and checksums). Copy installers you intend to archive to a different folder.
5. **Back up `C:\ProgramData\PlexCastExplorer` before an upgrade.** Run Setup as Administrator. Choose the service port, Private-profile Windows Firewall rule, and any explicitly permitted provider/VPN options. Do not uninstall your existing service first.
6. After installation, use **Start → Plex Cast Explorer → Set Gallery Password** if this is a new installation. On the server, browse `http://127.0.0.1:8765` (or your configured port), configure Plex, and index the libraries. Other trusted LAN devices sign in with the gallery password.

Setup installs an automatically starting service using the restricted `LocalService` account. Application data, tokens, SQLite index, and portraits remain under `C:\ProgramData\PlexCastExplorer`. Upgrades preserve that directory and apply a scoped firewall rule. End users running the compiled installer do **not** need Python or build tools.

For details see [Windows installation, service, upgrades and updates](docs/WINDOWS_INSTALLER.md), [local build gates](docs/BUILD_GATES.md), and [troubleshooting](docs/TROUBLESHOOTING.md).

## Features and security

- A–Z cast browser, search and filters; performers' credits and links into Plex.
- Plex actor portraits actively downloaded and cached during full or incremental sync, including scraper-independent custom-agent photos when Plex exposes a valid public HTTPS `Role.thumb` reference. Custom-host images are fetched through Plex's image transcoder after validation; private/LAN image destinations are blocked. Manual portrait overrides remain authoritative. Reviewable third-party artwork and incremental library synchronization are also supported.
- Separate gallery password and optional VPN-address-restricted remote administrator password.
- No change to Plex media files or metadata.

**Security boundary:** The web server uses plain HTTP. Use only a trusted LAN or an appropriately secured private VPN; **never forward the application port to the public Internet**. Do not expose it through an untrusted proxy on localhost. Provider API tokens and credentials must remain on the server. See [security](SECURITY.md), [privacy](docs/PRIVACY.md), and [remote admin](docs/REMOTE_ADMIN.md).

**Artwork priority:** Plex portraits first; authorized TMDB (explicit installer opt-in and API token) is the preferred external provider; ThePornDB (separate token) is queried only when TMDB has no usable portrait match. Wikimedia lookups remain disabled. The operator reports TMDB use is permitted for this deployment and is responsible for maintaining authorization within its actual scope. TMDB's approved logo and required attribution notice appear in the application's footer and About/Privacy page. The app does not grant redistribution rights in TMDB or ThePornDB imagery. Existing portraits are preserved. A new **Rescan unmatched performers** action requeues previous misses without deleting completed matches. See [artwork](docs/ARTWORK.md) and [third-party requirements](docs/THIRD_PARTY.md).

Development builds use unique `dev-` installer IDs. The final general-release installer has a separate, opt-in `-Release` build mode that requires a clean `dev` or `main` checkout and the final version number. A release-named binary built from `dev` is for final acceptance testing; only the exact source revision accepted for general availability is promoted to `main` and published.

## 1.0 feature freeze

The v1.0 feature set is frozen. Only targeted release-blocking bug fixes, security/privacy corrections, dependency and rights issues, compatibility fixes, regression tests, packaging and release documentation are allowed on `dev` until general availability. Do not add features, external provider integrations or unrelated refactors during stabilization.

## Development rules

All development is committed directly to **`dev`**. Keep only the `dev` and `main` branches; do not push to `main` without explicit maintainer approval. Do **not** run GitHub Actions, hosted CI, deployments or other GitHub-hosted code. The supported build entry point is **`BUILD-INSTALLER.cmd`**; the PowerShell build orchestrator compiles the EXE and Setup directly without a second batch-file helper. Everything is built and tested locally.

Built executables, service wrappers, local database files, tokens, logs, caches, and portraits must never be committed. Source tests can also be run manually with `python -m unittest discover -s . -p "test_*.py" -v`. Passing source/build gates **does not** replace actual Windows installer/upgrade/reboot tests on a disposable VM.

## Ownership, license, and contributions

Plex Cast Explorer is an independent community project, not affiliated with or endorsed by Plex, TMDB, ThePornDB, or Wikimedia. Source is published under the **Plex Cast Explorer Noncommercial Network Source-Share License 1.0**: all commercial use, including free internal use by for-profit organizations, requires the owner's prior written authorization. Custom terms have not been independently legally reviewed. Third-party art and trademarks are not licensed by this project. See [LICENSE](LICENSE), [licensing explanation](docs/LICENSING.md), and [legal review](legal/LICENSING_REVIEW.md).

Use [issues](https://github.com/Terridol/plex-cast-explorer/issues) for bugs or feature suggestions. Outside copyrighted code is not being accepted without appropriate contributor-rights agreements; see [contributing](CONTRIBUTING.md), [support](SUPPORT.md), and [maintainer policy](CONTRIBUTING.md).
