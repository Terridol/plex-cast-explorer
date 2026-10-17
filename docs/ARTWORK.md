# Artwork providers and attribution — v1.0

Plex Cast Explorer first uses actor portraits supplied by **your own Plex server**. It never bundles downloaded provider portraits or credentials inside Setup.

## Automatic sync and portrait selection

After Plex library synchronization completes, a background enrichment scan examines each new actor. The catalog saves the result in `enrichment_results`; completed matches, review decisions, and unmatched actors are not re-queried on ordinary subsequent syncs. Newly indexed actors are added automatically. Provider errors remain retryable, and operators can explicitly rescan unmatched actors.

1. **TMDB:** Preferred when explicitly enabled and configured. Name plus corroborating Plex credits are required; uncertain identities are sent to review.
2. **ThePornDB:** Second choice when TMDB has no corroborated candidate and its lookup did not fail. It may supersede a Plex-supplied portrait when identity confidence is sufficient.
3. **Plex:** Final fallback. Images from Plex Role metadata, person references and approved scraper URLs are retrieved on demand through the secured Plex image path rather than bulk-cached during sync.
4. **Review:** Ambiguous or conflicting external matches are queued without automatically changing the current image. A verified single credit with matching release year can qualify; name-only matches cannot.

The sync runs without waiting for tens of thousands of API lookups; the background enrichment worker reports its own progress. Previously completed actors do not consume provider calls on routine syncs. Changing provider availability or revisiting prior misses requires an explicit rescan operation.

TMDB lookups remain **disabled by default**: a saved token alone does not turn them on. Choose **Enable TMDB lookups** during Windows Setup and configure the API Read Access Token in Settings. The installer writes `CAST_EXPLORER_ENABLE_TMDB=1` to the WinSW service environment when selected. Prior installer settings may be remembered on upgrade. A valid authorization covering the actual media categories and distribution is necessary; the operator confirms this requirement has been resolved for their deployment. The project cannot independently certify third-party permission from a configuration toggle.

## TMDB attribution and conditions

TMDB requires one of its **unmodified approved logos** and a prominent non-endorsement statement. The footer and <a href="/privacy">About & Credits</a> section of the application link to the official TMDB site and include the notice:

> This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

Logo source: [TMDB's approved logo and attribution page](https://www.themoviedb.org/about/logos-attribution). Do not distort or recolor the linked official logo. TMDB terms restrict certain kinds of content and limit cached content to six months; application-side pruning keeps TMDB portrait overrides for at most 180 days, subject to the full agreement. Authorization should explicitly cover any adult-oriented deployments that use TMDB.

## Other providers and rights

**ThePornDB** use requires the operator's own token and compliance with provider terms and individual image/performer rights. No general artwork-redistribution license has been verified. **Wikimedia Commons remains disabled** because file-specific author, share-alike and license obligations are not yet automated.

Plex actor portrait bulk caching is disabled during normal library sync. Plex images are fetched on demand as fallbacks. The legacy bulk operation requires the explicit service environment variable `CAST_EXPLORER_BULK_PLEX_CACHE=1` and is not part of the standard installation.\n\nAll downloaded portrait overrides are stored locally under `portraits/`, with associated source metadata in SQLite. Plex metadata is read only and is not modified. Existing portraits remain available when TMDB cannot verify a match. When enabled, TMDB enrichment may replace an existing saved portrait or Plex thumbnail only with an unambiguous, corroborated match: either two overlapping credits with at least one verified release year, or one matching credit with an exact verified year and no conflicting role. Multiple competing candidates or missing corroboration require manual review without replacing existing art. If neither TMDB nor existing artwork provides a portrait, ThePornDB is the final fallback.

Keep provider tokens, user library metadata and cached images out of Git, release assets and public support reports. See [Third-party providers](THIRD_PARTY.md), [Privacy](PRIVACY.md) and [1.0 release checklist](RELEASE_CHECKLIST.md).
