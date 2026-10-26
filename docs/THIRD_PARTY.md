# Third-party providers: permitted-use considerations

Plex Cast Explorer is independently developed and is not affiliated with Plex, TMDB, ThePornDB, or Wikimedia. The source-code license **does not license any provider's data, artwork, or trademarks**.

## Bundled Windows Service Wrapper and build tools

The Windows installer includes **WinSW v2.12.0** as the service wrapper. WinSW is licensed under the MIT License; its upstream copyright and permission notice is retained in [`legal/WinSW-LICENSE.txt`](../legal/WinSW-LICENSE.txt) and bundled beside the installed application under `licenses/`. The builder verifies the published WinSW binary with a pinned SHA-256.

PyInstaller bundles Python and dependencies into the application executable. The Windows builder copies `LICENSE.txt` from the exact CPython runtime used for packaging into the installed `licenses/Python-LICENSE.txt`; absence of this license blocks the build. The project `NOTICE` is also installed. PyInstaller documents its GPL-with-bootloader-exception terms permitting distribution of generated bundles subject to the bundled dependencies' own licenses. Review the actual installed Python/PyInstaller versions, package license notices and any binary dependencies before general release.

## Plex

Users supply their own Plex tokens. Plex metadata and upstream images remain subject to Plex and underlying rights-holder terms. Keep all tokens out of commits, exports, logs and URLs sent to external providers.

## TMDB — primary opt-in provider

TMDB is the preferred provider when a Plex portrait is missing, but **disabled by default**. The operator reports permission for their intended use has been resolved; this statement is not an independent verification or a blanket license for anyone downloading the public installer. Each user remains responsible for meeting TMDB's [API Terms](https://www.themoviedb.org/api-terms-of-use), including restrictions on pornographic content and any separately granted authorization. Without permission to use TMDB for the specific deployment and its material, leave the TMDB installer task unchecked.

The app provides one [official, unmodified TMDB logo](https://www.themoviedb.org/about/logos-attribution) in the gallery footer and About/Privacy page, linked to [TMDB](https://www.themoviedb.org), beneath the app's own branding. It displays TMDB's required notice: "This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB." See TMDB's [FAQ](https://developer.themoviedb.org/docs/faq) and [logos policy](https://www.themoviedb.org/about/logos-attribution). The actual logo asset is loaded from TMDB's official site, unmodified, so browser access to that hostname is required to see it. Check its availability during real Windows acceptance testing.

A saved API token does not activate TMDB; the installer sets the service opt-in. Provider credits and portrait overrides are cached locally; TMDB portrait overrides older than 180 days and old enrichment records are pruned. If TMDB permission is revoked or expires, stop enabling the provider and remove or expire TMDB content as applicable. The project source license does not license TMDB trademarks, images or API use.

## ThePornDB — optional API token

Use only under the provider's currently applicable conditions. The maintainers have **not independently verified** any general right to redistribute provider images or use API responses for commercial deployment.

## Wikimedia Commons — BLOCKED in public v1.0

Media files use **individual licenses**. Verify the image's file page, photographer/author credit, applicable license, any share-alike requirements, and appropriate attribution before reuse. See [Wikimedia reuse guidance](https://www.mediawiki.org/wiki/Wikimedia_APIs/Content_reuse). The v1.0 app does not implement a complete file-license, photographer-credit and ShareAlike attribution record. Consequently Wikimedia lookups are **blocked even with legacy opt-in flags**, until a future explicitly reviewed release implements per-image compliance.

## Public repository

Never publish users' indexed media lists, portrait downloads, API keys, secrets, or provider data in source archives. A project license cannot grant third-party image rights.
