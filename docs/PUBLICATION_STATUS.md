# Publication status

**As of 2026-10-14: v0.4.2 source published on the public `main` branch.** This is a development-source publication, **not a supported production release or a security certification**. No tagged release has been published.

## Licensing

- [x] Adopt the [Plex Cast Explorer Noncommercial Network Source-Share License 1.0](../LICENSE).
- [x] Prohibit commercial use without prior written authorization, including internal use by for-profit organizations.
- [x] Require corresponding source sharing for qualifying distributed or network-served modified versions.
- [x] Publish clear terms in the [licensing guide](LICENSING.md).
- [x] Record the maintainer's decision to **proceed without paid legal review**.
- [ ] Establish a formal contributor-rights acceptance process before merging external copyrighted code.

**Notice:** The license is custom and not OSI-approved. Its enforceability has not been independently evaluated. Legal review is **not a project release requirement**.

## Source publication

- [x] Public GitHub repository: `Terridol/plex-cast-explorer`.
- [x] Complete 42-file source baseline committed, with the latest licensing documents preserved.
- [x] Application backend, web interface, Windows startup scripts, and tests included.
- [x] Local archive integrity verified and runtime credentials, databases, logs, and portrait cache excluded.
- [x] 21 unit tests passed locally; JavaScript syntax and Python bytecode compilation passed.
- [x] GitHub Actions tests passed on the published source branch ([successful run](https://github.com/Terridol/plex-cast-explorer/actions/runs/38597503476)).

## Before a supported release

- [ ] Review third-party metadata/image terms, caching and attribution (including TMDB branding).
- [ ] Assess token handling, admin access, authentication, LAN/remote behavior, and outbound image requests for security risks.
- [ ] Test a fresh Windows installation against a real Plex server and enabled provider APIs.
- [ ] Verify redistribution rights in any additional bundled assets and establish contributor consent.
- [ ] Configure applicable repository security protections and review CI results.
- [ ] Record explicit maintainer sign-off for a tagged software release.

A public codebase is not proof of fitness for deployment. Keep the application restricted to a trusted LAN or secured VPN; do not expose its HTTP server directly to the Internet.
