# Remote administration security model

Plex Cast Explorer supports **local admin by localhost** and **optional remote admin via a protected VPN**.

Remote administrators must complete two steps:

1. Sign into the gallery with the existing gallery password.
2. Connect from an explicitly allowed VPN client address and sign in at `/admin/login` with a separate, 16+ character administrator password.

The admin password is stored as PBKDF2-HMAC-SHA256 with an independent salt and signing key in `admin_auth.json`. The administrator cookie is signed with a separate secret, uses `HttpOnly` and `SameSite=Strict`, and expires after one hour. Failed admin logins are rate-limited. The server checks the **actual client socket address**, never `X-Forwarded-For` or other spoofable proxy headers, against `CAST_EXPLORER_REMOTE_ADMIN_CIDRS`.

With the allowlist unset or no admin password configured, all remote clients remain gallery-only. The normal gallery password alone never grants remote admin privileges.

**Transport caveat:** The built-in web server is HTTP. Admin credentials must only cross a VPN tunnel or separately secured private channel, never the Internet or an untrusted LAN. The service is not hardened for public Internet access. Do not forward port 8765 from your router and do not place an untrusted reverse proxy on localhost. See [Windows Setup](WINDOWS_INSTALLER.md).
