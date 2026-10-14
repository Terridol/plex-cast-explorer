# Installation and administration

## Requirements

- Python 3.10+; standard-library dependencies only.
- Plex Media Server reachable from the Cast Explorer host and a valid Plex token.
- A trusted local network. Windows is the primary supported platform.

## Install on Windows

1. Install Python and verify `python --version` in PowerShell.
2. Extract the release package to a permanent directory.
3. Run `set_password_windows.bat` and create a long, unique gallery password (12 characters minimum).
4. Run `start_windows.bat`. Keep its terminal open initially to see errors.
5. On the Plex server, browse `http://127.0.0.1:8765` and configure the Plex server URL and Plex token.
6. Start indexing. The initial run may be lengthy for large libraries.
7. On another device in the same trusted LAN, open `http://<SERVER-IP>:8765`; sign in with the gallery password.

**Network:** Allow TCP port 8765 through the host firewall for the relevant Private-network profile. Do not configure router WAN port forwarding. VLAN clients must be permitted by your router/firewall; see [Troubleshooting](TROUBLESHOOTING.md).

## Windows automatic startup

After verifying manual startup, stop the running process and choose **one** method:

- `install_autostart_windows.bat`: start when the current user signs in.
- `install_boot_task_windows.bat`: optional administrative Scheduled Task for boot-time operation. Review the script before running elevated.

Do not run multiple copies against the same SQLite database. To stop using automatic startup, use `uninstall_autostart_windows.bat` as applicable or remove the boot-time task from Task Scheduler.

## Linux/macOS

Set a gallery password with `python3 manage.py set-password`; run `sh start_linux_mac.sh`. Review firewall policies and create a system service manually if needed; the supplied launch script is not a systemd/launchd service.

## Local vs remote title links

Clients in detected LAN CIDRs use direct Plex Web links; other clients use hosted `app.plex.tv` links. Routed LANs can be added by copying `network.example.json` to `network.json`, adjusting CIDRs and the Plex LAN URL, and restarting. Never publish customized `network.json`.

## Upgrade safely

1. Stop the app and its startup task.
2. Back up `cast_explorer.db` plus its `-wal`/`-shm` companions, `config.json`, `auth.json`, `artwork_config.json`, `network.json`, and `portraits/`. Store backups securely.
3. Replace **source files only** from the new release.
4. Restart, hard-refresh the browser, and confirm stats, images, provider settings, and links. Avoid mixing source files from incompatible versions.

See the [release checklist](RELEASE.md) before publishing packages for other users.
