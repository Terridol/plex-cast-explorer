# Third-party sources and attribution

Plex Cast Explorer is an independent community tool. **Plex**, **TMDB**, **ThePornDB**, and **Wikimedia** are separate services. Their logos, names, API responses, and images are not automatically licensed under this source-code project's license.

## Plex

The application uses a user-provided Plex token to access the user's own Plex library metadata. It is not affiliated with or endorsed by Plex. Follow [Plex support documentation](https://support.plex.tv/) and keep tokens out of source control.

## TMDB

> This application uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.

[TMDB API terms](https://www.themoviedb.org/api-terms-of-use) require attribution and a correctly used **approved TMDB logo**. [Approved logos and brand guidelines](https://www.themoviedb.org/about/logos-attribution). The draft UI adds a text credit; **bundling and displaying the official approved logo is still a pre-release action**. Verify this requirement before any published application release. TMDB also limits some uses of its images and data; the maintainer must review any integration with adult-oriented libraries against the current provider terms.

## ThePornDB

Uses optional API credentials. Review provider permission, acceptable use, image licensing, and rate limits before use or redistribution; don't assume downloaded media are free to republish. No provider approval is implied.

## Wikimedia Commons

Image licenses vary **per file** and can require attribution and share-alike. Follow each original file's metadata/licensing, not merely the presence of the image on Commons.

## Source distributions

**Never commit or distribute** user `portraits/`, local Plex library databases, or provider API responses containing personal data in application source archives. Licensed app code and third-party artwork are separate categories.
