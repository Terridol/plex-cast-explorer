# Third-party providers: permitted-use considerations

Plex Cast Explorer is independently developed and is not affiliated with Plex, TMDB, ThePornDB, or Wikimedia. The source-code license **does not license any provider's data, artwork, or trademarks**.

## Bundled Windows Service Wrapper and build tools

The Windows installer includes **WinSW v2.12.0** as the service wrapper. WinSW is licensed under the MIT License; its upstream copyright and permission notice is retained in [`legal/WinSW-LICENSE.txt`](../legal/WinSW-LICENSE.txt) and bundled beside the installed application under `licenses/`. The builder verifies the published WinSW binary with a pinned SHA-256.

PyInstaller bundles Python and dependencies into the application executable. PyInstaller documents its GPL-with-bootloader-exception terms permitting distribution of generated bundles subject to the bundled dependencies' own licenses. Review the actual installed Python/PyInstaller versions, package license notices and any binary dependencies before general release.

## Plex

Users supply their own Plex tokens. Plex metadata and upstream images remain subject to Plex and underlying rights-holder terms. Keep all tokens out of commits, exports, logs and URLs sent to external providers.

## TMDB — OFF by default

TMDB's [API Terms](https://www.themoviedb.org/api-terms-of-use) prohibit API use in applications connected with pornographic content as TMDB determines, limit cached API content to **no more than six months**, and require the approved TMDB logo and prescribed attribution notice when the API is used. See [TMDB's logos and attribution guidance](https://www.themoviedb.org/about/logos-attribution). A saved token **does not** enable TMDB. The optional `CAST_EXPLORER_ENABLE_TMDB=1` flag must not be used unless the individual deployment and complete app attribution are compliant. The present text-only footer is **not** enough to satisfy the logo rule.

The application removes TMDB-source portrait overrides after 180 days and expires old lookup result records. This helps with cache duration but does not address every possible TMDB usage restriction.

## ThePornDB — optional API token

Use only under the provider's currently applicable conditions. The maintainers have **not independently verified** any general right to redistribute provider images or use API responses for commercial deployment.

## Wikimedia Commons — OFF by default

Media files use **individual licenses**. Verify the image's file page, photographer/author credit, applicable license, any share-alike requirements, and appropriate attribution before reuse. See [Wikimedia reuse guidance](https://www.mediawiki.org/wiki/Wikimedia_APIs/Content_reuse). The optional `CAST_EXPLORER_ENABLE_WIKIMEDIA=1` flag does not bypass these obligations.

## Public repository

Never publish users' indexed media lists, portrait downloads, API keys, secrets, or provider data in source archives. A project license cannot grant third-party image rights.
