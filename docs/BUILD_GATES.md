# Mandatory local regression and installer build gates

**Policy:** No GitHub-hosted builds, Actions, deployments or automatic tests. Maintain only `dev` and `main` branches.

Double-click `BUILD-INSTALLER.cmd`. **A discovery-based PowerShell parse preflight (all six production scripts, including its own validator) and all three gate stages are mandatory** and return a failing exit code if any required check fails. The builder keeps previous uniquely named installers in `output/`; it deletes any stale artifact for the current build ID before compiling and removes that build's installer/checksum if the final check fails.

| Stage | When | What blocks the build |
|---|---|---|
| Source regression | Before PyInstaller | Python syntax, all `test_*.py` unit tests, negative installer-mutation tests, version/AppId consistency, service upgrade, scoped firewall and postinstall readiness contracts, PowerShell script syntax (Windows), JS syntax if Node.js is present |
| Compiled executable smoke | After PyInstaller; before Inno Setup | The actual compiled EXE cannot launch with isolated temp data and a random local port, `--version` mismatches, frontend resources fail, version API fails, Host-header and CSRF protections regress, or isolated database cannot initialize |
| Installer artifact check | After Inno Setup | Compilation fails, Setup EXE missing/malformed/truncated, WinSW hash differs from pinned digest, version filename drifts, checksum sidecar absent/mismatched |

The source gate also requires the upstream WinSW MIT license notice to be included in the installer payload. The stable build mode is a **separate, explicit path** that shares these mandatory gates, not permission to skip them.

All tests are run on the developer's Windows PC, against a disposable temporary directory and ephemeral HTTP port. **The build does not touch the installed Windows service or your Plex library.** No credentials are read for executable smoke tests. A generated test report never contains access tokens.

Application-version extraction is checked as part of the **source gate** and rechecked in PowerShell before expensive dependency installation or EXE compilation. It must recognize the source `VERSION` declaration and agree with Inno Setup, the update checker, and service defaults. A PowerShell regex string uses single backslashes (e.g. `\s`), not doubled backslashes.

**Stable-release packaging:** after the entire [general-release checklist](RELEASE_CHECKLIST.md) passes and the maintainer approves promotion to `main`, set `VERSION` and all application/installer/service/update constants to the final `1.0.0` release, then invoke `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build_installer_windows.ps1 -Release` **from the clean `main` checkout**. The release mode omits development IDs from the Setup filename and installed display version, rejects `-rc` versions and dirty tracked files, and still runs the same source, EXE and installer artifact gates. Do not invoke it on `dev`.

### Reproduce the gates separately

```powershell
py -3 build_gate.py source
py -3 build_gate.py exe       # only after building dist/PlexCastExplorer
py -3 build_gate.py installer --build-id dev-YYYYMMDD-HHMMSSmmm-g12345678 # actual build ID required
```

### Important release boundary

**A build passing is not sufficient to claim the installer has been installed successfully.** The WinSW/SCM integration, service account ACLs, firewall rule on a real network profile, first installation, upgrade from a prior release, reboot and uninstall must also pass on a *disposable Windows VM or dedicated test PC*. Never run destructive installer tests automatically against the primary Plex server. A failure in any of those scenarios blocks public beta release; record the results in `docs/RELEASE_CHECKLIST.md`.

If Node.js is absent, the build prints a prominent message that JavaScript syntax was not parsed; the Python/backend and Windows installer/executable gates remain mandatory. Install Node.js for an additional JS syntax check prior to public beta.

## Unique development installer versions

Every local `dev` installer receives a build ID in the form `dev-YYYYMMDD-HHMMSSmmm-g<8-char-Git-SHA>`, or `dev-YYYYMMDD-HHMMSSmmm-s<8-char-source-fingerprint>` when Git is not available on PATH. Inno Setup requires this ID at compile time, embeds it into the displayed application version, and uses it in the setup filename. Example: `PlexCastExplorer-Setup-1.0.0-dev-20261014-203512123-g23a496e7-win-x64.exe`. The installer artifact gate requires the exact generated name and checksum. All previous output builds remain available for comparison; no build is deployed automatically. The stable installer `AppId` is **never changed** by a build ID.

## Repository workflow and promotion

Use GitHub Desktop to clone `Terridol/plex-cast-explorer`, select **`dev`**, then **Fetch origin → Pull origin** before running `BUILD-INSTALLER.cmd`. The local builder does not depend on any GitHub-hosted CI.

Keep exactly `dev` (active work) and `main` (maintainer-approved stable baseline). Do not create extra branches or automatically merge pull requests. Promotion into `main` requires explicit maintainer approval. `main` still has a legacy GitHub Actions workflow; confirm Actions are disabled in repository settings before pushing to it or publishing tags.
