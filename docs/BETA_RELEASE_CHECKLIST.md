# v0.4.7-beta public release readiness

**Status:** Release candidate; not yet published as an installable beta. Git policy: `dev` and `main` only; no GitHub-hosted execution.

## Completed locally
- [x] Application and installer source checked with local Python and JavaScript tools.
- [x] 36 automated tests pass in the development environment.
- [x] Inno Setup service configuration moved into `CurStepChanged(ssPostInstall)`, before the Finish screen.
- [x] Service setup now requires both Windows service status `Running` and a live HTTP response from the **expected** version.
- [x] Existing upgrades retain ProgramData and manage a Private-profile, subnet-scoped firewall rule.

## Windows verification needed before public beta
- [ ] Compile the updated installer on Windows with no errors; verify resulting installer hash.
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