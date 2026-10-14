# Publication status — 2026-10-14

**Public source:** `main` contains v0.4.2; `dev` contains the in-progress v0.4.4-beta security update. There is **no supported production release**. Being public on GitHub does not mean the LAN web service is safe to expose to the Internet.

## Verified so far

- [x] Source is public under a project-specific noncommercial network source-sharing license (not OSI-approved; independently unreviewed).
- [x] Exactly `main` and `dev` are maintained.
- [x] Browser POST requests must use JSON and reject cross-site fetch metadata.
- [x] Artwork URL and redirect checks include HTTPS/allowed host/standard TLS port validation.
- [x] TMDB and Wikimedia lookups are disabled by default; existing saved credentials do not automatically enable them.
- [x] TMDB artwork older than 180 days and old provider-match cache records are removed during startup and scheduled refresh.
- [x] Local Python, HTTP, and JavaScript syntax checks have been run for the development update.
- [x] Hosted Actions workflow removed from `dev` without launching hosted jobs.

## Checks that remain open

- [ ] **Real Windows/Plex smoke test:** validate existing database upgrade, server/LAN browser access, passwords, indexing, artwork previews, background enrichment, and local/remote Plex links.
- [ ] **Provider permissions:** TMDB explicitly restricts pornographic-associated applications and requires an approved logo if enabled; its text attribution alone is inadequate. Per-image Wikimedia licensing and ThePornDB terms need a deployment-specific check.
- [ ] Confirm authorized redistribution of all included source/assets and establish contributor licensing acceptance.
- [ ] Review private-vulnerability reporting, secret-scanning, and branch permissions in GitHub Settings.
- [ ] Verify no secrets or private data were ever included in earlier git history.
- [ ] Obtain maintainer approval before tagging or promoting a supported release.

Local validation cannot substitute for testing against the user's actual Plex server. The application still serves HTTP and is intended for a trusted LAN or secured private VPN, **not a public WAN port forward**.
