# Third-party providers: permitted-use considerations

Plex Cast Explorer is independently developed and is not affiliated with Plex, TMDB, ThePornDB, or Wikimedia. The source-code license **does not license any provider's data, artwork, or trademarks**.

## Bundled Windows Service Wrapper and build tools

The Windows installer includes **WinSW v2.12.0** as the service wrapper. WinSW is licensed under the MIT License; its upstream copyright and permission notice is retained in [`legal/WinSW-LICENSE.txt`](../legal/WinSW-LICENSE.txt) and bundled beside the installed application under `licenses/`. The builder verifies the published WinSW binary with a pinned SHA-256.

PyInstaller bundles Python and dependencies into the application executable. The Windows builder copies `LICENSE.txt` from the exact CPython runtime used for packaging into the installed `licenses/Python-LICENSE.txt`; absence of this license blocks the build. The project `NOTICE` is also installed. PyInstaller documents its GPL-with-bootloader-exception terms permitting distribution of generated bundles subject to the bundled dependencies' own licenses. Review the actual installed Python/PyInstaller versions, package license notices and any binary dependencies before general release.

## Plex

Users supply their own Plex tokens. Plex metadata and upstream images remain subject to Plex and underlying rights-holder terms. Keep all tokens out of commits, exports, logs and URLs sent to external providers.

## TMDB — BLOCKED in public v1.0

TMDB's [API Terms](https://www.themoviedb.org/api-terms-of-use) prohibit connecting TMDB API/content to pornographic uses and require approved-logo attribution and notice for approved API integrations. See [official FAQ](https://developer.themoviedb.org/docs/faq). **The v1.0 distribution cannot initiate TMDB API calls or new TMDB image downloads**; saved tokens and previous environment flags cannot reenable the integration. We have **not** obtained written permission, so no TMDB brand logo or misleading active-API attribution is included in the release. Previously saved local artwork is left untouched to avoid destructive migrations; individual users must assess any required purge or removal.

The application removes TMDB-source portrait overrides after 180 days and expires old lookup result records. This helps with cache duration but does not address every possible TMDB usage restriction.

## ThePornDB — optional API token

Use only under the provider's currently applicable conditions. The maintainers have **not independently verified** any general right to redistribute provider images or use API responses for commercial deployment.

## Wikimedia Commons — BLOCKED in public v1.0

Media files use **individual licenses**. Verify the image's file page, photographer/author credit, applicable license, any share-alike requirements, and appropriate attribution before reuse. See [Wikimedia reuse guidance](https://www.mediawiki.org/wiki/Wikimedia_APIs/Content_reuse). The v1.0 app does not implement a complete file-license, photographer-credit and ShareAlike attribution record. Consequently Wikimedia lookups are **blocked even with legacy opt-in flags**, until a future explicitly reviewed release implements per-image compliance.

## Public repository

Never publish users' indexed media lists, portrait downloads, API keys, secrets, or provider data in source archives. A project license cannot grant third-party image rights.
