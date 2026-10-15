# v0.4.7-beta public release readiness

**Status:** Release candidate; not yet published as an installable beta. Git policy: `dev` and `main` only; no GitHub-hosted execution.

## Completed locally
- [x] Application and installer source checked with local Python and JavaScript tools.
- [x] Python unit/regression and fail-closed mutation tests pass on development source; counts change as tests are added and must be recorded for each release candidate.
- [x] Mandatory local build pipeline added: source regression, compiled EXE HTTP smoke, and installer artifact/digest checks (Windows-specific stages still pending).
- [x] Inno Setup service configuration moved into `CurStepChanged(ssPostInstall)`, before the Finish screen.
- [x] Service setup now requires both Windows service status `Running` and a live HTTP response from the **expected** version.
- [x] Existing upgrades retain ProgramData and manage a Private-profile, subnet-scoped firewall rule.

## Windows verification needed before public beta
- [ ] Pull `dev` in GitHub Desktop and run `BUILD-INSTALLER.cmd` on Windows; confirm that the PowerShell preflight, every regression gate, compiler, EXE smoke test and installer checksum all pass. Earlier Windows builds failed because of updater PowerShell syntax and unsupported WinSW `refresh`.
- [ ] Clean Windows installation: confirm configured port, password setup, firewall scope, and service ready **before** Finish.
- [ ] In-place upgrade from v0.4.6-beta: preserve gallery index, portraits, settings, credentials, and installer choices.
- [ ] Reboot: service must start without interactive sign-in.
- [ ] Negative startup test on a disposable machine: occupy the selected port and confirm Setup reports a failure instead of showing normal success.
- [ ] Uninstall/reinstall: verify removal of service/firewall and retention of user data.
- [ ] Confirm remote administration is VPN-only from configured IP ranges, requiring a separate admin password.
- [ ] Inspect release assets and Git history for accidentally included secrets or personal data.
- [ ] Confirm GitHub Actions are **disabled in repository settings** before creating a version tag or publishing release assets; `main` retains workflow triggers.
- [ ] Publish official beta installer with SHA-256 checksum and test the explicit, user-initiated Check for Updates flow.

## Known publishing limitations
- TMDB is disabled by default; the optional provider has content-use restrictions and approved-logo requirements that remain incomplete. Do not enable in prohibited environments or claim compliance.
- Third-party artwork has independent licensing and attribution requirements.
- The application uses HTTP: trusted LAN/private VPN only, **never** public WAN forwarding.
- The unsigned beta can cause Windows SmartScreen warnings; do not instruct users to bypass antivirus.
- Custom noncommercial source license is not independently legally reviewed.

**Minimum beta gate:** Windows clean install, upgrade, reboot, failure/rollback and privacy checks; published checksum and clear limitations; explicit maintainer go-ahead.
## Release publication and ownership checks

The following gates are required *in addition to* passing the local builder:

- Confirm no credentials, databases, private metadata, cached portraits, or service logs appear in the repository, Git history, installer, or publication assets.
- Check redistribution rights for all bundled dependencies and third-party material. The project's custom noncommercial license has not undergone independent legal review.
- Keep TMDB off by default; resolve any approved-logo, attribution, caching, and permitted-use questions before enabling it in a supported public release. Artwork from other providers carries separate rights.
- Validate clean installation, upgrade with data retention, reboot, uninstall/reinstall, LAN gallery authentication, VPN-only administrator login, and a deliberate installer failure on a disposable Windows test machine.
- Confirm publisher, release notes, documentation, exact versioned installer filename, and SHA-256. The executable is currently unsigned; publishing an unsigned beta requires clear notice.
- Confirm repository Actions are disabled before creating GitHub release tags (legacy triggers still exist on `main`). Never run GitHub-hosted builds or automation.
- Accept third-party copyrighted contributions only after obtaining necessary rights or appropriate signed contributor agreements.

Do not claim a stable or certified release, and do not publish tags or modify `main` without maintainer approval.
