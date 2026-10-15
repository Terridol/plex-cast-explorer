# Artwork providers and rights — v1.0

Plex Cast Explorer first uses portrait metadata from **your own Plex server**. Its installer does not ship downloaded actor portraits, provider API credentials, Plex media, or cached provider content.

## Available in 1.0

- **Plex metadata and artwork:** Used by default through the operator's authenticated Plex Media Server, subject to Plex's terms and the underlying image rights.
- **ThePornDB:** Optional, only after the operator configures their own API token. Confirm the provider's current API terms, image rights, privacy/publicity rights, and any applicable attribution before using portraits. The maintainers have not obtained or verified a general artwork redistribution license. External requests transmit performer names and filmography context to the provider.

## Disabled in 1.0

- **TMDB:** No new API lookups, credential enrollment, automatic portrait matching, or portrait downloads. TMDB's [API terms](https://www.themoviedb.org/api-terms-of-use) restrict uses connected with pornographic content and require approved-logo attribution. This app supports adult-media libraries and has not obtained written authorization for that use. The old `CAST_EXPLORER_ENABLE_TMDB=1` flag and saved tokens cannot enable it. The setup wizard no longer offers the option.
- **Wikimedia Commons:** No new lookups or Wikimedia image downloads. File-specific copyright/attribution obligations are not yet represented and verified by the app. The old `CAST_EXPLORER_ENABLE_WIKIMEDIA=1` flag cannot enable it.

Existing locally saved portraits and SQLite records are **not purged by upgrading**. Previously cached artwork remains the operator's responsibility under the relevant rights and retention terms; local preservation is not proof of permission to publish, distribute, or display a third party's images. If a provider revokes rights, remove affected cached content as required by those terms.

## Matching and review

ThePornDB candidates must match the normalized performer name and corroborating Plex titles, release years, and nonconflicting characters; ambiguous results require manual review. A matching title is not conclusive proof of identity. Automatic assignment is conservative and cannot change Plex metadata.

## Distribution policy

Never commit or publish personal Plex metadata, API tokens, cached portraits, artwork databases, exported performer data, or provider logos/assets without express rights. No public Internet forwarding of this HTTP application. See [third-party legal requirements](THIRD_PARTY.md), [privacy](PRIVACY.md) and the [1.0 release checklist](RELEASE_CHECKLIST.md).
