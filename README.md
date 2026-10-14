# Plex Cast Explorer

> **Pre-release repository — application source is not yet published.**

Plex Cast Explorer is a self-hosted web application for browsing performers across movie and TV libraries on one Plex Media Server. It aims to provide a searchable cross-library cast directory and credit-aware portrait matching.

## Features under development

- Unified actor and actress directory across movie and TV libraries
- Performer search, credits, and cross-library title links
- LAN-aware links to local Plex, with hosted Plex links for remote users
- Optional portrait lookup using external metadata providers
- Automatic portrait selection when identity evidence is sufficient; review queue otherwise
- Local indexing without modifying original Plex media

## Publication status

**Current internal development build: v0.4.2.** Source publication is pending review of the custom license, third-party metadata/artwork terms, and security. **No public release or installable package is available in this repository yet.**

See [Publication status](docs/PUBLICATION_STATUS.md). Please wait until the contributor licensing terms are finalized before submitting code contributions.

## Licensing

The intended license is **noncommercial source-available with network source-sharing obligations**. It is not an OSI-approved open-source license. The custom text is currently under legal review and is not yet an operative license here.

**All rights reserved pending publication of the applicable license.** Public repository visibility does not authorize commercial use or redistribution. Licensing inquiries: [@Terridol](https://github.com/Terridol).

## Security and privacy

The application is intended for trusted LANs or appropriately secured private networks, **not direct Internet exposure**. Never commit Plex tokens, API keys, passwords, cached portraits, personal library data, or runtime databases. See [Security policy](SECURITY.md).

## Third parties

Independent community project. Not affiliated with or endorsed by Plex, TMDB, ThePornDB, or other metadata providers. Third-party APIs, artwork, and names are subject to their own terms.

---
**Status:** Public project placeholder; code release pending.
