# Windows installer, upgrades and updates — v0.4.7-beta

The new Windows wizard **replaces the manual service-migration process**. It is built with [Inno Setup 6](https://jrsoftware.org/isinfo.php) and installs Plex Cast Explorer as an Automatic (Delayed Start) Windows service under the restricted `LocalService` account. The compiled installer includes the PyInstaller application and a SHA-256-pinned WinSW service wrapper, so **end users do not need Python, PyInstaller or Inno Setup**.

> **Build status:** Source and application tests passed locally, but the Windows Inno compiler and Windows-service integration have **not yet been exercised** in this environment. Build and test the installer on Windows before promoting to `main`.

## Build one real Setup.exe on Windows

1. Extract the source kit into a clean directory. Use Windows 10/11 x64 with Python 3.10+ (3.13 tested).
2. Double-click **`BUILD-INSTALLER.cmd`**. It calls `BUILD-EXE.cmd` if necessary, downloads or installs Inno Setup 6 if needed, and obtains the pinned WinSW service executable (preferring the verified copy from the existing installation).
3. The produced installer is `output/PlexCastExplorer-Setup-0.4.7-beta-win-x64.exe` with a matching `.sha256` checksum file. Distribute the compiled installer and checksum, **not** any local ProgramData files.
4. Scan the installer and review its digital signature before distribution. It is **not Authenticode-signed** until the maintainer signs it; do not advise disabling Windows SmartScreen or antivirus.

Compiling is a local Windows operation; the process does **not run GitHub Actions**.

## First installation

Run the Setup EXE as Administrator. The wizard offers:

- Installation folder (normally `C:\Program Files\PlexCastExplorer`).
- TCP port (default `8765`).
- Private-network Windows Firewall rule scoped to **LocalSubnet** and approved VPN CIDRs (default checked; never creates a WAN/router port forward).
- Optional TMDB integration (default off; review its content and attribution restrictions).
- Optional remote administration: allowlisted VPN client IP/CIDR (default off). Configure a **distinct** admin password with the installed Start Menu shortcut.
- Stable or beta update channel and optional desktop shortcut.

Setup starts the service **before the Finish screen** and waits for a successful localhost HTTP response from the expected application version. A failed service start or missing response is an installer error, not an apparent success.

The service is configured to run under `NT AUTHORITY\LocalService`. Runtime files are stored in `C:\ProgramData\PlexCastExplorer`, with access restricted to Administrators, SYSTEM and the service identity. On a fresh install, use the **Set Gallery Password** shortcut in the Start Menu before accessing the gallery from LAN devices. The app does not yet have a first-run Plex token wizard; configure Plex through the browser on the server.

## Upgrade an existing installation

**Do not uninstall the working service first.** Run a newer Setup EXE over the existing install, choose settings, and let it stop the service, update program files and WinSW service configuration, replace the managed firewall rule, and restart the service. Existing data remains in ProgramData: passwords, Plex tokens, SQLite index, portrait cache and approval history. The upgrade creates a timestamped snapshot under `C:\ProgramData\PlexCastExplorer\backups\pre-upgrade-...` for the database and settings (including SQLite WAL/SHM files if present). The installer does not import files from the old `D:\plex-cast-explorer` folder.

For an existing pre-Inno service, the first wizard installation uses the same service name, Program Files and ProgramData paths. It validates the existing WinSW wrapper path and `LocalService` account, retains the service registration, updates automatic delayed startup through Windows `sc.exe config`, and then starts the service with the revised adjacent XML. **WinSW 2.12 does not support the `refresh` command**; the installer never calls it. The local build gate explicitly rejects reintroducing that command. Review wizard options: TMDB, remote admin and firewall scopes can be changed from the old settings when creating the first Inno-managed installation.

**Safety:** Always retain an independent ProgramData backup before an upgrade. A service that fails to restart should be recovered from its logs before retrying. Database formats may evolve in future versions; never restore a database snapshot into an incompatible newer version without checking the release notes.

## Updating later

Choose **Start → Plex Cast Explorer → Check for Updates**. The local PowerShell checker queries the project's **published GitHub releases** (not branch commits) using HTTPS. It respects the stable/beta channel, reports newer releases, and provides the official release page.

For a fully interactive download and install, run from the installed program directory:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\check_updates.ps1 -DownloadAndInstall
```

It only downloads a release installer when GitHub exposes an asset **SHA-256 digest**. It verifies the downloaded bytes against that digest and **prompts for explicit confirmation** before opening the regular Setup wizard via UAC. It never silently installs a new version. Hash checking is not the same as a publisher Authenticode signature; verify release ownership and signing independently.

There is **no automatic self-update job or unattended downloader**. If no installer release is available (or no digest is published), the checker links to the official release page without installing anything.

## Diagnosing service setup failures

If Setup stops with `Service configuration failed (exit code 1)`, the installer did not complete service configuration. **Do not uninstall the existing service or remove ProgramData.** The current development installer logs the underlying PowerShell exception to:

- `C:\\ProgramData\\PlexCastExplorer\\logs\\installer-last-error.txt` — short cause shown in Setup's error dialog.
- `C:\\ProgramData\\PlexCastExplorer\\logs\\installer-error-details.log` — timestamped script error and source position. May reveal local paths; review before sharing.

An earlier installer only displayed a generic exit code 1, which is **not enough information to establish the root cause**. On a failed upgrade, check the current service state before trying Setup again:

```powershell
Get-Service PlexCastExplorer -ErrorAction SilentlyContinue |
    Format-Table Name,Status,StartType
Get-ChildItem "$env:ProgramData\\PlexCastExplorer\\logs" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 8 Name,LastWriteTime,Length
```

The app/database in `ProgramData` should be retained. An unsuccessful service health check can indicate a Windows service issue, an app process startup failure, an occupied TCP port, access permissions, or a mismatched app version; **the installer error code alone does not identify which**.

The build gate verifies the diagnostic code is present but **is not a substitute for a genuine Windows install/upgrade test in a disposable VM**.

## Firewall and VPN

The installer manages only its own named inbound rule `PlexCastExplorer-Inbound-Private` (and cleans up the older legacy app rule if present). It allows TCP on the selected port only on a **Private** Windows network profile and only from the `LocalSubnet` plus optionally selected VPN client CIDRs. To reach from another subnet, explicitly enter the trusted VPN client IP/CIDR at setup or rerun the installer. It never permits unsolicited public Internet access. A VPN interface classed Public requires a separately evaluated limited rule; do not open the port to all Public interfaces. Remote administration uses a separate 16-character-minimum password and cannot be accessed without a configured VPN source allowlist.

## Removal and data retention

Uninstall from Windows Installed Apps. This stops and removes the service, program files, and the installer's firewall rule. **It intentionally preserves `C:\ProgramData\PlexCastExplorer` including database, tokens, passwords, portraits, backups and logs**, allowing later reinstallation. To erase private data permanently, remove that folder separately after backing it up if needed.
