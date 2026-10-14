# Public release checklist

This checklist is a project-level quality gate, **not a claim of compliance or security certification**.

## Checks before tagging a supported application release

- [x] Publish the custom noncommercial/source-sharing `LICENSE` after owner approval. **No paid legal review required by the project; enforceability is not independently verified.**
- [ ] Verify ownership or redistribution permission for all source files and bundled third-party assets; publish a contact for commercial permission.
- [ ] Validate all files and Git history contain no credentials, personal library databases, logs, private images, or sensitive URLs; rotate any previously exposed secrets.
- [ ] Complete TMDB-approved logo and attribution in the running UI; review provider licensing and restrictions, particularly for adult-oriented media.
- [ ] Run automated tests on supported Python versions and Windows/Linux, plus a live smoke test on a real Plex server with test libraries.
- [ ] Document any newly discovered security limitations; verify no known critical security issues are unresolved.
- [ ] Enable GitHub secret scanning, push protection, Dependabot alerts (where applicable), and private vulnerability reporting.
- [ ] Restrict repository write access; protect `main` with required passing checks and review for contributor changes.

- [ ] Finalize and operationalize the CLA for new contributions before accepting outside copyrighted patches.

## For each release

1. Update changelog and version string together; follow Semantic Versioning for version labels.
2. Run `python -m unittest discover -s . -p 'test_*.py' -v` and compile checks.
3. Test clean installation, gallery login, localhost administration, Plex sync, LAN/remote links, provider lookups, and upgrade with preserved settings.
4. Tag `vX.Y.Z`, publish a GitHub Release, and publish source ZIP with a SHA-256 checksum. Never include local config, index, logs, or cached portraits.
5. State supported release versions and known limitations in the release notes. Publish relevant security advisories or mitigations when appropriate.

Review [OpenSSF OSPS Baseline](https://baseline.openssf.org/), [GitHub Community Standards](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions), and relevant provider terms regularly. **No full OWASP/penetration audit has been performed.**

## Windows installer releases

Compile `BUILD-INSTALLER.cmd` on Windows, test upgrading an existing installed service with a database backup and validate firewall scopes. Publish the compiled `PlexCastExplorer-Setup-<version>-win-x64.exe` with SHA-256 checksum as a GitHub Release asset, without running GitHub-hosted jobs. Verify GitHub exposes the asset SHA-256 digest before using the automatic downloader. The updater is explicitly user-initiated and does not install software unattended.
