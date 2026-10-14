# Windows EXE + boot-start service (v0.4.5-beta)

This is a **local Windows build and installer kit**, not a Windows-tested production release. GitHub-hosted compilation or CI is not used.

## What changes

- The application becomes `PlexCastExplorer.exe` using PyInstaller one-folder packaging.
- WinSW 2.12.0 runs it as an **Automatic (Delayed Start)** Windows service under **`NT AUTHORITY\LocalService`**, not LocalSystem.
- Program code lives in `C:\Program Files\PlexCastExplorer`; runtime data lives in `C:\ProgramData\PlexCastExplorer`.
- During migration, an explicitly named existing source data folder (for example `D:\plex-cast-explorer`) supplies config, authentication, index and portraits. It is **not deleted**.
- Your former manual launch and scheduled-task methods must be stopped before installation. Do not run two processes against the same library index.

The installer downloads **WinSW-x64.exe v2.12.0** from its [official tagged release](https://github.com/winsw/winsw/releases/tag/v2.12.0), and verifies SHA-256 `05b82d46ad331cc16bdc00de5c6332c1ef818df8ceefcd49c726553209b3a0da` (also listed by the independent Scoop package manifest). Abort if antivirus flags a downloaded executable; **do not disable antivirus or bypass a block**.

## 1. Back up, then build locally

1. Save a **complete backup** of `D:\plex-cast-explorer` including config files, any database sidecars and portraits.
2. Stop the existing batch-file window. Check `http://127.0.0.1:8765` is no longer responding.
3. Install a supported 64-bit Python 3.10+ on Windows, then extract this v0.4.5-beta source kit somewhere outside `C:\Program Files`.
4. From that directory in **regular PowerShell**, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows_exe.ps1 -InstallPyInstaller
```

This downloads PyInstaller from PyPI when not present and builds an EXE locally. It does not run anything on GitHub.

## 2. Install the service

Open **PowerShell as Administrator** in the extracted kit directory and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_service_windows.ps1 -ExistingDataDir 'D:\plex-cast-explorer' -EnableTMDB -AllowPrivateLanFirewall
```

The script prompts for confirmation of your backup, checks no other instance is listening on port 8765, migrates selected runtime data without overwriting data already present in ProgramData, installs WinSW, and starts the service. The `-EnableTMDB` flag explicitly enables TMDB lookups; only use it for deployments consistent with TMDB conditions (see below). The optional `-AllowPrivateLanFirewall` opens TCP/8765 on Windows **Private** profiles only. No router or WAN ports are opened.

**Verify:** In Windows Services (`services.msc`) check `PlexCastExplorer` is Running and Automatic (Delayed Start). Browse `http://127.0.0.1:8765` and check the actor directory, settings, artwork and existing database. Reboot only after a successful initial test and verify the service starts by itself.

To stop/start from elevated PowerShell: `Stop-Service PlexCastExplorer` / `Start-Service PlexCastExplorer`.

## 3. Remote administration over VPN only

**Do not open port 8765 to the Internet.** Use a private VPN such as UniFi Teleport/WireGuard or Tailscale. Your own VPN client IP must be explicitly allowed; use a **single client `/32`** (IPv4) or `/128` (IPv6), not a whole unrestricted internet-facing range. The installer accepts a comma-separated list.

Example for a hypothetical VPN laptop address `100.101.22.12`:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_service_windows.ps1 -ExistingDataDir 'D:\plex-cast-explorer' -EnableTMDB -RemoteAdminCIDRs '100.101.22.12/32' -AllowPrivateLanFirewall
```

When remote administration is enabled, the installer prompts you to set a **distinct administrator password of 16+ characters**. From the *approved VPN client*, first log in using your gallery password, then open `http://10.10.10.30:8765/admin/login` and provide the separate administrator password. Administrator sessions last one hour. Admin users can change the Plex connection and artwork settings and run indexing; ordinary gallery users cannot.

Your allowed VPN client must be able to reach the service through the relevant Windows firewall interface. A VPN interface classified as Public may require a **narrowly scoped VPN-only firewall rule**; the Private-only installer rule deliberately does not open the service to all public-profile interfaces. Ask for assistance rather than widening all Public-network firewall access.

Remote administration is **disabled by default**; the HTTP service itself does not provide TLS. The VPN supplies transport encryption. Avoid local reverse proxies that forward untrusted traffic to loopback, as that bypasses the localhost administrator check.

## 4. Change remote admin password later

In elevated PowerShell on the Windows host:

```powershell
$env:CAST_EXPLORER_DATA_DIR = "$env:ProgramData\PlexCastExplorer"
& "$env:ProgramFiles\PlexCastExplorer\PlexCastExplorer.exe" --set-admin-password
```

This invalidates old admin sessions. To change allowed VPN client IPs, stop the service, edit only `CAST_EXPLORER_REMOTE_ADMIN_CIDRS` inside the protected `PlexCastExplorerService.xml` file under Program Files, then restart. Never expose the service through a WAN port forward.

## 5. Rollback

Run `uninstall_service_windows.ps1` as Administrator. This removes the service **but preserves all ProgramData**, the older `D:\plex-cast-explorer` folder, and the compiled installation files. You can resume the old manual installation if necessary, but only **one copy of Cast Explorer should be running at a time**. Do not merge two independently modified SQLite databases.

## TMDB limitation

Explicit opt-in does not establish the right to use TMDB metadata or artwork for every Plex library. [TMDB API Terms](https://www.themoviedb.org/api-terms-of-use) restrict certain pornographic-content associations and impose approved-logo attribution and other requirements. This beta does **not** certify compliance; review the terms for your exact usage before enabling the flag.
