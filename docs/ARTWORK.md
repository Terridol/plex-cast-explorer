# Artwork providers and attribution — v1.0

Plex Cast Explorer first uses actor portraits supplied by **your own Plex server**. It never bundles downloaded provider portraits or credentials inside Setup.

## Automatic actor matching and artwork source priority

The application scans the entire Plex library, then enriches actors in the
background. **Only one identity decision is used** by new searches and by
previously queued reviews.

1. **TMDB** is the preferred portrait. A credible TMDB actor replaces any
   saved ThePornDB image or Plex fallback.
2. **ThePornDB** is used if no credible TMDB portrait is found. It replaces
   Plex art but cannot replace saved TMDB art.
3. **Plex** is an on-demand fallback and is never falsely labeled TMDB.

An exact normalized actor name and one matching production are sufficient to
automatically accept a **single credible provider identity**. Character-name
differences do not reject the match. One missing/incorrect film title or
release year is an **informational warning** if the remaining filmography
corroborates the performer. A unique title whose *only* year disagrees
substantially is not corroborated.

Manual review is reserved for multiple plausible identities (unless optional
IMDb evidence independently resolves the tie) or genuinely contradictory /
untrustworthy results. Failed provider lookups are retryable errors, not
requests for human identity approval. Missing results retain Plex fallback.

Actor cards show their actual source, and non-blocking metadata warnings appear
on the profile. An automatic scan clears old single-person review entries,
and a one-time refresh attempts to upgrade prior ThePornDB portraits to TMDB
without removing the old portrait when no better one is found.

The user library and Plex metadata are always read-only. A saved TMDB image
is fetched only with an explicitly enabled TMDB integration and proper API
credentials; no external lookups are required to browse existing actor data.

TMDB remains **disabled by default**. Set **Enable TMDB lookups** during
Windows Setup and configure the API Read Access Token in Settings. The
installer uses the `CAST_EXPLORER_ENABLE_TMDB=1` service setting when opted in.
Provider permissions and attribution requirements still apply.

## TMDB attribution and conditions

TMDB requires one of its **unmodified approved logos** and a prominent non-endorsement statement. The footer and <a href="/privacy">About & Credits</a> section of the application link to the official TMDB site and include the notice:

> This product uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

Logo source: [TMDB's approved logo and attribution page](https://www.themoviedb.org/about/logos-attribution). Do not distort or recolor the linked official logo. TMDB terms restrict certain kinds of content and limit cached content to six months; application-side pruning keeps TMDB portrait overrides for at most 180 days, subject to the full agreement. Authorization should explicitly cover any adult-oriented deployments that use TMDB.

## Other providers and rights

**ThePornDB** use requires the operator's own token and compliance with provider terms and individual image/performer rights. No general artwork-redistribution license has been verified. **Wikimedia Commons remains disabled** because file-specific author, share-alike and license obligations are not yet automated.

Plex actor portrait bulk caching is disabled during ordinary sync; Plex
thumbnails load on demand as a fallback. External portrait files are kept
locally under `portraits/` with source attribution in the actor database.
Previously saved files are not deleted when a provider cannot find artwork.
Provider tokens and private library data must not be committed to Git.

See [Third-party providers](THIRD_PARTY.md),
[Privacy](PRIVACY.md), and [Release checklist](RELEASE_CHECKLIST.md).

## Optional IMDb identity corroboration (personal, non-commercial use)

IMDb is **not** an artwork provider and the application never scrapes IMDb pages.
When two or more TMDB identities remain plausible, an optional local IMDb
`knownForTitles` dataset can provide an additional independent title/year
cross-check. TMDB's supported `external_ids` endpoint supplies the candidate's
IMDb person ID. A candidate is selected by IMDb only when exactly one candidate
has positive known-for evidence and the others have less; the candidate must
still pass the local filmography confidence checks. Missing IMDb evidence never
counts against someone. If the dataset is missing, ambiguous profiles remain
in review as before.

To install or **update** the local IMDb identity dataset:

1. Download `name.basics.tsv.gz` and `title.basics.tsv.gz` from
   https://datasets.imdbws.com/ on your own computer, subject to IMDb's
   current personal/non-commercial dataset terms. Do not redistribute these files.
2. Stop the Windows **Plex Cast Explorer** service temporarily. Open an
   elevated Command Prompt (Run as administrator). Set the exact installed
   data folder before launching the EXE:

   ```bat
   set "CAST_EXPLORER_DATA_DIR=%ProgramData%\PlexCastExplorer"
   cd /d "C:\Program Files\Plex Cast Explorer"
   PlexCastExplorer.exe --update-imdb "C:\Downloads\name.basics.tsv.gz" "C:\Downloads\title.basics.tsv.gz"
   ```

   Adjust the installation/download paths. If the EXE is in another directory,
   navigate there instead. For a source checkout, set `CAST_EXPLORER_DATA_DIR`
   as needed and use `python app.py --update-imdb ...`.
   Restart the service after the update finishes.
3. Repeat the same command whenever you want fresher IMDb data. It writes
   `imdb-identity.sqlite` in the configured application data folder and
   atomically replaces the previous dataset only after successful import.

The update can take significant time and temporary disk space for full IMDb
datasets. Run it when the application service is stopped to avoid Windows file
locking. After updating, pending ambiguous actors may be retried through the
existing review workflow; already accepted portraits are not changed.
IMDb `knownForTitles` is a **limited set of highlights**, not a complete
filmography, and must never be used as negative identity evidence.

