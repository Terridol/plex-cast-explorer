# Artwork providers and identity checks

Cast Explorer first uses portrait metadata supplied by Plex. Optional third-party sources include **TMDB** (token required), **ThePornDB** (token required), and **Wikimedia Commons**. Use Settings from the server's loopback address to configure providers.

## Provider defaults and explicit opt-in

- **Plex portraits** are used by default.
- **ThePornDB** is optional and requires the user's own API token; its provider terms and rate limits still apply.
- **TMDB** is **disabled by default**, even if a token was saved in an earlier version. Its provider terms restrict use involving pornographic content. Only enable it if the actual deployment is permitted by those terms: set `CAST_EXPLORER_ENABLE_TMDB=1` in the **Cast Explorer server process environment**, and restart. A saved token alone does not activate TMDB.
- **Wikimedia Commons** is **disabled by default** until individual image licensing and attribution are checked. Enable with `CAST_EXPLORER_ENABLE_WIKIMEDIA=1` only if the operator has a process for verifying image-specific rights.
- With either opt-in flag unset, the corresponding provider is not contacted. These settings do not grant permission to use third-party images.

On Windows PowerShell for a single manual launch, set `$env:CAST_EXPLORER_ENABLE_TMDB='1'` before launching `start_windows.bat`. Scheduled startup needs separate per-task environment configuration. Do not set machine-wide values merely for convenience.

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
