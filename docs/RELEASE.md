# Release process (local execution only)

The repository publishes source code. A supported, installable public release requires the checks below; no paid legal review is required by the maintainer.

## 1. Local quality checks

Run `python -m compileall -q app.py manage.py test_app.py test_security_images.py test_release_guardrails.py` followed by `python -m unittest discover -s . -p 'test_*.py' -v`, and run `node --check static/app.js` if Node.js is installed.

Test with a fresh, disposable local database; also test an upgrade with a backed-up existing database. Confirm galleries, portrait previews, sign-in/sign-out, library sync, job cancellation, and credits links.

## 2. Security and privacy

Verify the distribution contains **no** `auth.json`, `config.json`, `artwork_config.json`, `network.json`, SQLite files, tokens, logs, cached portraits, or local user data. Test incorrect Host, Origin, and Content-Type headers. The bundled HTTP server is for private LANs and VPNs only; **never forward port 8765 to the public Internet**.

## 3. External provider permissions

Providers' API keys, data, trademarks, and images have separate terms. Plex images belong to their upstream owners. TMDB is disabled by default and should not be enabled in prohibited contexts. Its optional enabled integration still needs an **approved TMDB logo** and other attribution requirements. Wikimedia image licenses are file-specific. ThePornDB usage must be verified by each operator.

TMDB-derived portraits expire from local caching after 180 days. Provider opt-in alone does not grant rights.

## 4. Publication

Only use `dev` and `main`. The owner has prohibited GitHub-hosted jobs; verify Actions are disabled on `main` before publishing changes to it. After owner approval and real installation tests, promote validated source. Publish a clean archive with SHA-256 checksum and versioned release notes, **without executing GitHub-hosted build/release automation**. Never mark unverified checks complete.
