# Changelog

## Unreleased — v0.4.4-beta (local tests only)

- Reject cross-site browser POSTs and require JSON request bodies, including for loopback administration.
- Reject unsupported chunked POST requests and stop disclosing exception details to LAN clients.
- Expire saved TMDB portraits and cached provider-match data after 180 days.
- Extend tests for request validation and artwork expiry.
- Remove the automatic GitHub-hosted tests workflow from `dev`.
- Publish updated third-party, security, branching, and release procedures.
- Public development source only; no tagged production release or live Plex-server integration verification.

## Unreleased — v0.4.3-beta (local validation only)

- Reject unrecognized HTTP Host headers to reduce DNS-rebinding risk for localhost administration.
- Require explicit opt-in for TMDB and Wikimedia providers. Existing credentials stay saved but do not silently activate these providers.
- Update the portrait Settings screen to reflect whether each provider is actually enabled.
- Extend regression tests covering provider opt-in and Host validation.
- Work staged on a development branch. No GitHub-hosted workflows were run for these changes at the maintainer's request.

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
