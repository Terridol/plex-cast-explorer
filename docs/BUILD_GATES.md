# Mandatory local regression and installer build gates

**Policy:** No GitHub-hosted builds, Actions, deployments or automatic tests. Maintain only `dev` and `main` branches.

Double-click `BUILD-INSTALLER.cmd`. **All three stages are mandatory** and return a failing exit code if any required check fails. The builder removes any previously compiled Setup EXE before compiling and removes the generated installer/checksum if the final artifact check fails.

| Stage | When | What blocks the build |
|---|---|---|
| Source regression | Before PyInstaller | Python syntax, all `test_*.py` unit tests, six deliberate installer-mutation tests, version/AppId consistency, service upgrade, scoped firewall and postinstall readiness contracts, PowerShell script syntax (Windows), JS syntax if Node.js is present |
| Compiled executable smoke | After PyInstaller; before Inno Setup | The actual compiled EXE cannot launch with isolated temp data and a random local port, `--version` mismatches, frontend resources fail, version API fails, Host-header and CSRF protections regress, or isolated database cannot initialize |
| Installer artifact check | After Inno Setup | Compilation fails, Setup EXE missing/malformed/truncated, WinSW hash differs from pinned digest, version filename drifts, checksum sidecar absent/mismatched |

All tests are run on the developer's Windows PC, against a disposable temporary directory and ephemeral HTTP port. **The build does not touch the installed Windows service or your Plex library.** No credentials are read for executable smoke tests. A generated test report never contains access tokens.

### Reproduce the gates separately

```powershell
py -3 build_gate.py source
py -3 build_gate.py exe       # only after building dist/PlexCastExplorer
py -3 build_gate.py installer # only after Inno Setup and checksum generation
```

### Important release boundary

**A build passing is not sufficient to claim the installer has been installed successfully.** The WinSW/SCM integration, service account ACLs, firewall rule on a real network profile, first installation, upgrade from a prior release, reboot and uninstall must also pass on a *disposable Windows VM or dedicated test PC*. Never run destructive installer tests automatically against the primary Plex server. A failure in any of those scenarios blocks public beta release; record the results in `docs/BETA_RELEASE_CHECKLIST.md`.

If Node.js is absent, the build prints a prominent message that JavaScript syntax was not parsed; the Python/backend and Windows installer/executable gates remain mandatory. Install Node.js for an additional JS syntax check prior to public beta.

## Unique development installer versions

Every local `dev` installer receives a build ID in the form `dev-YYYYMMDD-HHMMSSmmm-g<8-char-Git-SHA>`, or `dev-YYYYMMDD-HHMMSSmmm-s<8-char-source-fingerprint>` when Git is not available on PATH. Inno Setup requires this ID at compile time, embeds it into the displayed application version, and uses it in the setup filename. Example: `PlexCastExplorer-Setup-0.4.7-beta-dev-20261014-203512123-g23a496e7-win-x64.exe`. The installer artifact gate requires the exact generated name and checksum. All previous output builds remain available for comparison; no build is deployed automatically. The stable installer `AppId` is **never changed** by a build ID.
