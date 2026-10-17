# Artwork providers and attribution — v1.0

Plex Cast Explorer first uses actor portraits supplied by **your own Plex server**. It never bundles downloaded provider portraits or credentials inside Setup.

## Provider priority

1. **Plex:** Use an existing Plex actor image without contacting an *additional metadata provider*. This includes images provided to Plex by a nonstandard metadata agent when Plex includes the image reference in the cast `Role.thumb` field. Plex-relative URLs are fetched directly from Plex when requested; custom-scraper public HTTPS URLs are resolved through Plex's authenticated photo-transcode endpoint after destination safety checks. `metadata://` and `media://` portrait references are requested from Plex's own metadata-file endpoint. If `Role.thumb` is absent but Plex provides a valid person metadata link in `Role.key` or `Role.ratingKey`, sync checks the Plex person record for an image. Where neither contains a portrait, the external TMDB-first enrichment path remains necessary. Arbitrary private-network image hosts remain blocked. Custom provider portraits may require that Plex itself can reach and transcode the image.
2. **TMDB (preferred when enabled):** For actors with or without existing artwork, query TMDB **only when enabled through the Windows installer** and a TMDB API token is configured. This is the preferred external artwork provider. Require a matching performer name, a nonempty profile image, and corroborating Plex credits for automatic enrichment. If no matching TMDB portrait is found, proceed to step 3.
3. **ThePornDB:** Queried only when TMDB produces no verified portrait, Plex has no thumbnail, and TMDB did not report a provider error. Existing Plex artwork is never replaced by TPDB. Requires its own API token, independent of TMDB. Title/credit overlap is still required for automatic saving.
4. **Review / unmatched:** Uncertain matches stay for manual review. A provider error blocks automatic assignment. Unmatched actors can be explicitly rescanned after improving provider settings. Successfully applied portraits, skipped/review decisions and Plex metadata are not reset by the unmatched-rescan action.

TMDB lookups remain **disabled by default**: a saved token alone does not turn them on. Choose **Enable TMDB lookups** during Windows Setup and configure the API Read Access Token in Settings. The installer writes `CAST_EXPLORER_ENABLE_TMDB=1` to the WinSW service environment when selected. Prior installer settings may be remembered on upgrade. A valid authorization covering the actual media categories and distribution is necessary; the operator confirms this requirement has been resolved for their deployment. The project cannot independently certify third-party permission from a configuration toggle.

## TMDB attribution and conditions

TMDB requires one of its **unmodified approved logos** and a prominent non-endorsement statement. The footer and <a href="/privacy">About & Credits</a> section of the application link to the official TMDB site and include the notice:

> This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

Logo source: [TMDB's approved logo and attribution page](https://www.themoviedb.org/about/logos-attribution). Do not distort or recolor the linked official logo. TMDB terms restrict certain kinds of content and limit cached content to six months; application-side pruning keeps TMDB portrait overrides for at most 180 days, subject to the full agreement. Authorization should explicitly cover any adult-oriented deployments that use TMDB.

## Other providers and rights

**ThePornDB** use requires the operator's own token and compliance with provider terms and individual image/performer rights. No general artwork-redistribution license has been verified. **Wikimedia Commons remains disabled** because file-specific author, share-alike and license obligations are not yet automated.

Plex actor portrait bulk caching is disabled during normal library sync. Plex images are fetched on demand as fallbacks. The legacy bulk operation requires the explicit service environment variable `CAST_EXPLORER_BULK_PLEX_CACHE=1` and is not part of the standard installation.\n\nAll downloaded portrait overrides are stored locally under `portraits/`, with associated source metadata in SQLite. Plex metadata is read only and is not modified. Existing portraits remain available when TMDB cannot verify a match. When enabled, TMDB enrichment may replace an existing saved portrait or Plex thumbnail only with an unambiguous, corroborated match: either two overlapping credits with at least one verified release year, or one matching credit with an exact verified year and no conflicting role. Multiple competing candidates or missing corroboration require manual review without replacing existing art. If neither TMDB nor existing artwork provides a portrait, ThePornDB is the final fallback.

Keep provider tokens, user library metadata and cached images out of Git, release assets and public support reports. See [Third-party providers](THIRD_PARTY.md), [Privacy](PRIVACY.md) and [1.0 release checklist](RELEASE_CHECKLIST.md).
