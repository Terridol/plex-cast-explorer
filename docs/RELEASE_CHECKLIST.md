# Plex Cast Explorer 1.0 — General release checklist

**Status: FEATURE LOCKED, v1.0.0 SOURCE PREPARED, NOT PUBLISHED.** Target GA version: `1.0.0`. The most recent maintainer-confirmed installed working build was `0.4.7-beta`. This file is the single source of truth for general-availability approval.

**Change policy:** On `dev`, only narrowly scoped release-blocking fixes, security/privacy hardening, dependency/attribution work, regression tests, installer compatibility, and release documents. No new features, unrelated refactors, providers, branches, GitHub-hosted builds or automatic releases. Do not update `main` before approval.

## Feature scope frozen for v1.0

- Windows 10/11 x64 installer, compatible in-place upgrades, auto-start service, Private-profile scoped firewall.
- Plex movie/TV cast and credits indexing, actor gallery, search, filters, library links and incremental synchronization.
- Portrait cache, manually reviewed external art, conservative matching, passwords and optional VPN-restricted remote administration.
- Existing runtime data, configuration, database and portraits under `C:\ProgramData\PlexCastExplorer`.

## Verified evidence

- [x] Maintainer confirmed the **0.4.7-beta** source/build gates, Windows installer, upgrade and application worked on the Windows host after prior fixes.
- [x] Final version `1.0.0` is set in application, installer, service, updater and version regression tests. Source is not itself a distribution-tested binary.
- [x] Source on `dev` has a single CMD builder, six PowerShell scripts and explicit local build gates.
- [x] Audited the current tracked `dev` tree: 47 files, no committed generated executables, databases, logs or private artwork, no duplicate file blobs and no broken internal Markdown links. This is **not** a complete Git-history or packaged-binary audit.
- [x] Scanned the text content of all 47 currently tracked files for common GitHub/AWS/API credential formats and PEM private-key markers; no matching patterns were found. This does **not** prove older commits or unusual secret formats are clean.
- [ ] **Run the final 1.0.0 local build** from latest `dev` using `BUILD-INSTALLER.cmd`. Record Git SHA, 73+ regression tests, JS syntax check, EXE smoke, exact installer output and SHA-256. Previously passing 0.4.7 does not validate the candidate.

## Mandatory Windows release acceptance — use a disposable VM/test PC

- [ ] Clean install with configured port, password enrollment, Private firewall and `NT AUTHORITY\LocalService` identity; verify service and local HTTP API before Finish.
- [ ] In-place upgrade from the 0.4.7-beta installed build, including a legacy `LocalSystem` service; confirm all credentials, index, portraits, review history, port/options, firewall and identity retained or migrated correctly.
- [ ] Reboot without interactive sign-in; verify delayed service startup, index availability and LAN gallery authentication.
- [ ] Simulate an occupied port and failed service startup; confirm error is surfaced and a working backup/recovery procedure exists.
- [ ] Uninstall/reinstall on disposable Windows; verify service/firewall cleanup and **ProgramData survives**.
- [ ] Confirm VPN-restricted administrator logins reject unauthorized networks and gallery-only sessions cannot access admin controls.
- [ ] Validate offline/no Plex connection behavior, invalid credentials, corrupt configuration and recovery instructions.
- [ ] Validate live ThePornDB enrichment for performers with large scene-credit responses (previously truncated at 1,000,001 bytes), then confirm retrying failed lookups processes saved errors without deleting applied portraits.

## Security, legal and publication gates

- [ ] Audit entire Git **history**, source archive and installer payload for tokens, databases, local portraits, logs, user metadata or unexpected binaries; rotate anything historically leaked.
- [x] Bundle the original WinSW MIT license notice alongside the installed wrapper; enforce its inclusion through source tests.
- [x] Require the CPython runtime license from the build interpreter and include project NOTICE in the Windows installer.
- [ ] Review Python/PyInstaller versions and all remaining binary dependencies, bundled licenses and third-party attribution; ensure no external/provider artwork is bundled.
- [x] Fail-closed disable TMDB and Wikimedia API use and new portrait downloads in public v1.0; remove misleading TMDB Setup option and credential UI while preserving existing local data on upgrade.
- [ ] Verify ThePornDB's current API terms and artwork rights with the provider; use only user-provided tokens and never bundle downloaded portraits or third-party metadata. No general redistribution permission has been established.
- [ ] Independently assess the custom noncommercial source-share license if public enforcement/commercial permissions matter. Never call it an OSI open-source license.
- [ ] Review session, HTTP Host, CSRF, file-path, credential, provider redirect and API handling for general distribution; independent penetration testing recommended.
- [ ] Confirm restricted LAN/private-VPN HTTP-only deployment; never publicly forward the port or imply native TLS protection.
- [ ] Confirm **GitHub Actions disabled in repository Settings** before tagging or changing `main` (existing `main` contains workflow triggers).
- [x] Provide a stable-named installer mode requiring final semver and a clean `dev` or `main` checkout. Build from `dev` for final acceptance; publish only after the exact tested source is approved and promoted to `main`.
- [ ] Run and validate the stable-named `1.0.0` Setup from the final approved source, sign if possible, calculate SHA-256 and verify an external download.
- [ ] Verify explicit user-consented update check, released asset digest, publisher identity, release notes, privacy/support/contact instructions and license notices.
- [ ] Obtain explicit maintainer go/no-go to promote `dev` to `main`, tag and publish the 1.0.0 installer.

**No-go:** Any unchecked mandatory item blocks a public 1.0 general-availability claim. Document any formally waived item and reason rather than silently marking it complete.
