# Plex Cast Explorer

**Status: Public development repository · v0.4.2 source staging (not a certified or production release)**

Plex Cast Explorer is a self-hosted web application for browsing performers across movie and TV libraries on one Plex Media Server. Its goals include a searchable cross-library cast gallery, credit-aware portrait matching, a review queue, and LAN-aware links to Plex.

## Features

- Unified actor and actress gallery and cross-library filmographies
- Actor search, filtering, and links to local Plex or app.plex.tv
- Optional portrait lookup via Plex and third-party metadata providers
- Credit-aware enrichment and review of uncertain matches
- Locally stored index and portrait overrides, without altering your Plex media

## Licensing

**Plex Cast Explorer is source-available, not OSI-approved open source.** It is licensed under the [Plex Cast Explorer Noncommercial Network Source-Share License 1.0](LICENSE).

- **All commercial use requires prior written permission.** This also applies to internal deployment by for-profit organizations, even without a fee.
- Permitted noncommercial use, modification, and distribution are subject to the full license.
- Redistribution of modified copies requires their corresponding source under the same terms.
- Providing a modified version to others over a network requires an accessible public source link in that version's interface.
- Individual unpublished modifications used privately without distribution or network sharing do not have to be published.

**The custom license has not been independently legally reviewed.** No claim is made that all provisions will be enforceable in every jurisdiction. No commercial rights are granted by repository visibility. For commercial permission, contact [@Terridol](https://github.com/Terridol).

## Publication status

The repository is public, but **source publication and application release checks are separate**. Check [publication status](docs/PUBLICATION_STATUS.md) for remaining technical, security, licensing-rights, and third-party provider checks. The v0.4.2 source package remains in staging until it is committed; do not interpret this README as a published installer.

## Security and privacy

This application is designed for trusted local networks. Its built-in HTTP server is **not suitable for direct public-Internet exposure**. Do not forward its port from your router to the Internet. Use a secured private network or VPN.

Do not commit Plex tokens, API credentials, passwords, indexed library data, cached portraits, or local configuration. See [SECURITY.md](SECURITY.md).

## Third-party services and artwork

Plex Cast Explorer is independent of Plex, TMDB, ThePornDB, and Wikimedia. Metadata, images, APIs, and trademarks remain subject to each provider's terms. The project license does not grant rights to third-party content. Work remains to verify provider-specific attribution, caching, and use restrictions before release.

## Contributing

Project discussion and issue reports are welcome. **Please do not submit third-party copyrighted source code or images, or external code contributions that require unagreed licensing rights.** Contributor terms, technical checks, and release procedures will be documented as development progresses.
