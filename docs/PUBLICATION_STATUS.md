# Publication status

**As of 2026-10-14: NOT RELEASED.** The GitHub repository is public for project visibility and planning. The application source is withheld pending the checks below.

## Release gates

- [x] Repository created under `Terridol/plex-cast-explorer`
- [x] v0.4.2 source package assembled, excluding runtime data
- [x] 21 synthetic automated tests pass locally
- [ ] Legal review of proposed noncommercial network source-share license and contributor rights agreement
- [ ] Verify permission to distribute every source file and bundled asset
- [ ] Third-party provider review: permitted TMDB / ThePornDB / Wikimedia uses, caching, and in-app attribution
- [ ] Security review for local web server, HTTP authentication, image proxy, and secret handling
- [ ] Real installation / provider smoke tests on Windows and Linux
- [ ] Enable repository security features and a green CI run
- [ ] Explicit maintainer sign-off for public source release

No release tag should be published until these gates are satisfied.

## Why the code is not on the default branch yet

A public GitHub repository makes files visible instantly. The custom licensing terms and contributor rights are not yet legally reviewed, and provider compliance has not been established. Publishing under an unreviewed license would not provide the requested assurance against commercial use or closed-source forks. The current license draft remains an offline review artifact.

## Intended license

Noncommercial source-available with mandatory source-sharing for qualifying distributed or network-served modified versions. It is not an OSI-approved open-source license.

## Local development

Until publication, maintain the working code and local configuration outside this repository. Do not upload Plex library metadata, secrets, runtime database files, logs, or cached portraits.
