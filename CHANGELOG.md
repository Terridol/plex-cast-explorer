# Changelog

## dev — Windows installer and repository cleanup

- Repaired invalid `test_installer_spec.py` syntax and removed duplicated test case/footer, which would have prevented regression tests from starting.
- Consolidated the Windows builder into `BUILD-INSTALLER.cmd` plus `build_installer_windows.ps1`; removed the redundant nested `BUILD-EXE.cmd`.
- Merged overlapping branching, general release, and maintainer documentation into the build guide, beta checklist, and contribution guide.
- Removed an unadopted contributor-agreement draft (the policy against accepting outside copyrighted patches remains in effect).
- Extended repository hygiene tests to detect duplicate class methods, multiple entry-point guards, and broken legal-document links.
- Verified one active batch launcher, six purpose-specific PowerShell scripts, and no redundant build or migration files remain on `dev`.
- Repaired `installer/check_updates.ps1`: restored its terminated filename pattern and removed a duplicated download block; added regression tests that reproduce both faults.
- Repaired `build_gate.py` and `test_build_gate.py`: removed accidentally duplicated module/test sections and restored the updater-guard regular expression.
- Kept one supported Windows installation entry point (`BUILD-INSTALLER.cmd`), building the executable directly in the PowerShell orchestrator, without a second batch helper.
- Removed obsolete direct-run launchers, redundant `manage.py`, unused standalone PyInstaller and service-migration scripts, obsolete installation documents, and unused PR metadata.
- Reduced nested duplicate source-test execution; retained mandatory PowerShell syntax preflight, source regression and mutation tests, compiled EXE smoke, Inno Setup compilation, and installer artifact/digest check.
- Updated all installation, contributor, provider, troubleshooting and release documents to match the Windows service deployment.
- Kept application index, provider, authentication and cache logic unchanged except for retiring an outdated password instruction; preserve the existing Plex database, tokens and portraits during upgrades.
- Real Windows clean-install, in-place upgrade, reboot and uninstall testing remains mandatory before publishing a public beta.

## v0.4.7-beta — Windows setup startup verification

- Correct malformed PowerShell build script introduced by dev build-ID versioning: remove duplicated installer sections and restore complete Git revision/build-ID regex.
- Run Windows PowerShell AST syntax validation **before launching** the installer build; reject syntax errors before compiling or changing service state.
- Extend fail-closed regression checks to catch duplicated installer body, malformed Git SHA regex, or missing PowerShell preflight.


- Distinguish every `dev` installer by an automatically generated UTC build timestamp and Git SHA/source fingerprint; embed the ID in the Setup filename and Installed Apps version.
- Preserve older installer builds rather than overwriting identical filenames; validate the build identifier in local gates and updater asset matching.


- Fix confirmed Windows upgrade failure: WinSW v2.12 rejected the unsupported `refresh` command and left the service stopped.
- Preserve existing service registration; verify wrapper path/account; apply automatic delayed-start via Windows SCM; restart with updated WinSW XML.
- Add fail-closed regression checks forbidding `refresh`, including a mutation test that reproduces the previously released failure.
- Capture underlying Windows setup exceptions and surface them in the installer instead of reporting only exit code 1.


- Introduce mandatory local fail-closed build gates: source regression/negative tests, compiled EXE HTTP smoke, and installer hash/artifact checks.
- Document GitHub Desktop `dev` pull-and-build workflow; exclude generated installers and service wrapper binaries from source control.
- Start and verify the Windows service before the installer Finish page appears.
- Verify the actual application responds on localhost with the expected version; SCM/WinSW Running alone is insufficient.
- Report service start and health-check failures clearly instead of presenting false success.
- In-place upgrade continues to retain credentials, database, artwork, and managed Private-network firewall settings.
- Local regression tests passed; clean-install, reboot and final Inno compilation must be verified on Windows.

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
