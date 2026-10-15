# Branching and validation policy

Plex Cast Explorer maintains exactly two branches:

| Branch | Purpose |
| --- | --- |
| `main` | Approved, stable development baseline |
| `dev` | Active work and locally validated changes |

Changes are committed directly to `dev`. After successful local checks and explicit maintainer approval, `dev` can be promoted to `main`. No extra branches or pull requests are required.

## No GitHub-hosted execution

The maintainer prohibits GitHub Actions, hosted builds, deployments, and other GitHub-run processes unless separately authorized. **The GitHub Actions workflow was removed from `dev`.** The older workflow may still exist on `main`; do not push to `main` until Actions have been disabled in repository settings or the automatic triggers can be safely removed without launching jobs.

## GitHub Desktop workflow

1. Clone `Terridol/plex-cast-explorer` once in GitHub Desktop.
2. Use **Current Branch → dev**. Click **Fetch origin** and **Pull origin** before building.
3. In the checked-out repository folder, double-click `BUILD-INSTALLER.cmd` to run the mandatory local source, compiled EXE and installer artifact gates and build Setup.exe.
4. Commit development updates only to `dev`; share installer files separately when a beta is approved. Do not commit `output/`, `dist/`, `build/`, `installer-assets/`, local database or credentials.

The source/build gate is documented in [BUILD_GATES.md](BUILD_GATES.md). An installer that compiles is not proof that Windows installation or upgrade succeeded; test those in an isolated VM before a public release.

Run tests locally:

```powershell
python -m compileall -q app.py manage.py test_app.py test_security_images.py test_release_guardrails.py
python -m unittest discover -s . -p "test_*.py" -v
```

Check JavaScript syntax locally using Node.js: `node --check static/app.js`. Do not publish stable release tags or deploy without explicit approval.
