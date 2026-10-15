# Plex Cast Explorer

A self-hosted, cross-library performer directory for **Plex Media Server**. Browse an A–Z portrait gallery, search cast members, and see their movies and shows across every indexed library.

**Development version:** v0.4.7-beta · **Python:** 3.10+ (standard library) · **Host:** Windows (primary); Linux/macOS launchers available

**Licensing:** Public **source-available** project — all commercial use requires prior written authorization; qualifying modifications must share their source. [License summary](docs/LICENSING.md) · [Full terms](LICENSE). *These project-specific terms have not been independently legally reviewed.*

> **Security:** Designed for use on a trusted local network only. The built-in web server uses HTTP, not HTTPS. **Never forward port 8765 to the Internet.**
>
> **Project status:** Public development source; live interoperability, security, and provider-attribution verification remain incomplete. Do not treat this as a certified production release.

## Features

- Cross-library actor directory with full-text name search, filters, and filmographies.
- Local Plex title links on configured home subnets; hosted Plex links for remote visitors.
- Plex-provided portraits plus optional TMDB, ThePornDB, and Wikimedia searches.
- Credit-aware portrait enrichment, candidate review, and automated matching for eligible single candidates.
- Local SQLite indexing, cached portrait overrides, incremental library sync, and Windows startup helpers.
- LAN gallery password; administrative operations available only from the server's loopback connection.

## Windows Setup wizard / boot-start service / updates

Windows installations use **[the new installer](docs/WINDOWS_INSTALLER.md)**. The Setup wizard offers install folder, port, a **Private-profile and local-subnet-restricted Windows Firewall rule**, TMDB opt-in, VPN-restricted remote administration, release channel, and shortcuts. It installs an automatic Windows service using the restricted LocalService identity and preserves `ProgramData` on upgrades and uninstall.

**Build the real Setup.exe on Windows:** check out the `dev` branch with GitHub Desktop and double-click `BUILD-INSTALLER.cmd` in your local repository folder. The result is `output/PlexCastExplorer-Setup-0.4.7-beta-win-x64.exe`. End users of that resulting Setup.exe do **not** need Python or build tools. An offline Windows compiler/integration smoke test remains outstanding; do not treat the installer as production-certified yet.

**Updating:** Choose **Start → Plex Cast Explorer → Check for Updates**. The updater checks published releases; a newer installer runs only after explicit user confirmation and digest verification. No background self-updater or GitHub Actions are used.

## Developer workflow (GitHub Desktop)

The `dev` branch is the **single source of truth** for active development; no downloaded builder ZIPs are needed. In GitHub Desktop, clone [Terridol/plex-cast-explorer](https://github.com/Terridol/plex-cast-explorer), switch **Current Branch** to `dev`, then use **Fetch origin → Pull origin** to get updates. Open the repository in Explorer and double-click **`BUILD-INSTALLER.cmd`**.

The mandatory **local, fail-closed build gates** run automatically: Python regression and installer policy tests (42 passing in the latest Linux-side validation), a compiled EXE HTTP smoke test, Windows PowerShell syntax validation and installer checksum checks. Generated `build/`, `dist/`, `output/`, `installer-assets/` and `*.spec` files are ignored by Git and must not be committed. See [Build gates](docs/BUILD_GATES.md).

**No GitHub-hosted tests or builds**, no new branches, and no promotion to `main` without maintainer approval. Passing the build gates is distinct from real Windows install/upgrade/reboot tests on a disposable VM.

## Quick start (Windows)

1. Install **Python 3.10+**, ensuring `python --version` works in a new terminal.
2. Download the source ZIP from the repository (or a published release archive when available) and extract it to a permanent directory (for example `C:\Apps\plex-cast-explorer`).
3. Run `set_password_windows.bat` to configure the gallery password.
4. Run `start_windows.bat`.
5. On the **server itself**, visit `http://127.0.0.1:8765`, enter the Plex URL (usually `http://127.0.0.1:32400`) and authentication token, then index your libraries.
6. On another trusted LAN device, open `http://<SERVER-IP>:8765` and sign in using the gallery password.

The Windows firewall may require an inbound rule for TCP 8765 on the appropriate **Private** profile. **UniFi port forwarding is not required** for local access.

[Full installation & configuration](docs/INSTALLATION.md) · [Art and identity matching](docs/ARTWORK.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)

## Data safety

The app **does not alter Plex media or Plex metadata**. Your Plex token, provider keys, indexed titles/performers, review decisions, and downloaded images remain **on your own host**; the external providers may receive search terms and movie/show-credit queries when enabled. These runtime files must never be committed:

`config.json` · `auth.json` · `artwork_config.json` · `network.json` · `cast_explorer.db*` · `portraits/` · `*.log`

See [Security](SECURITY.md) and [Privacy & data flow](docs/PRIVACY.md) for limitations and handling details.

## For contributors

- [Contributing guide](CONTRIBUTING.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [Support](SUPPORT.md)
- [Architecture](docs/ARCHITECTURE.md) · [Maintainers](docs/MAINTAINERS.md) · [Release process](docs/RELEASE.md) · [Readiness audit](docs/PUBLICATION_STATUS.md) · [Changelog](CHANGELOG.md)
- Run tests locally: `python -m unittest discover -s . -p 'test_*.py' -v`
- Local tests only; automatic GitHub Actions are disabled on `dev`.

## Third-party names, images and licensing

Plex Cast Explorer is an **independent community project**, not affiliated with or endorsed by Plex, TMDB, ThePornDB, or Wikimedia. Names, trademarks, cast metadata and portraits belong to their respective owners. An application source-code license does **not** grant rights to redistribute provider images.

**TMDB notice:** This application uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB. See [Third-party credits and provider requirements](docs/THIRD_PARTY.md). An approved TMDB logo still needs to be included before claiming full compliance with TMDB branding terms.

**License:** **Plex Cast Explorer Noncommercial Network Source-Share License 1.0**. Commercial use, including internal use by for-profit businesses, requires prior written permission. Noncommercial forks must preserve the license and applicable source-sharing requirements. The custom terms have **not** been independently reviewed; no guarantee of universal enforceability is made. See [Licensing](docs/LICENSING.md) · [License limitations](legal/LICENSING_REVIEW.md) · [Release checklist](docs/RELEASE.md).
