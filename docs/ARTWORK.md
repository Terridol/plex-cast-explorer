# Artwork providers and identity checks

Cast Explorer first uses portrait metadata supplied by Plex. Optional third-party sources include **TMDB** (token required), **ThePornDB** (token required), and **Wikimedia Commons**. Use Settings from the server's loopback address to configure providers.

## Matching logic

1. Index performers and their movie/TV credits from the selected Plex libraries.
2. Look for provider records with an exact normalized performer name.
3. Compare production titles, available release years, and credited roles.
4. A **sole qualifying** candidate with a corroborating production credit and no known conflicting evidence may be applied automatically; other candidates enter the review queue.
5. Manually inspect sources and portraits for uncertain matches. You can accept, reject, skip, or override an artwork selection.

**Limitations:** A single matching title, even with a matching year or role, is not definitive proof of identity. Cast labels, translation differences, aliases, episode-level credits, and provider errors can produce false positives or false negatives. Automatic results should be spot-checked.

Portrait overrides are stored in `portraits/` and an SQLite record. Plex metadata is not modified. The app contacts provider APIs and image hosts when retrieving images and searching matches; provider-specific rate limits and terms apply.

## Source rights

Downloaded portraits are **not** covered by the project's source-code license. Before redistribution or public display, review original licensing, attribution, and privacy rights, including Wikimedia file-specific licenses. See [Third-party providers](THIRD_PARTY.md).
