# Privacy and local data

Plex Cast Explorer is self-hosted. The code does not include a cloud account or telemetry collector.

| Data | Where it lives or goes |
| --- | --- |
| Plex URL and token | Server-side `config.json`; sent to your configured Plex server. |
| Gallery password verifier/session signing secret | Server-side `auth.json`; never store a plaintext password. |
| Artwork provider credentials | Server-side `artwork_config.json` (or environment overrides). ThePornDB tokens are sent only to its API on authenticated requests. Existing TMDB tokens may remain from older installs but are not used by 1.0. |
| Movie/show titles, actors, credits, and review decisions | Local `cast_explorer.db`. |
| Downloaded portrait overrides | Local `portraits/`; not distributed with source. |
| Optional artwork searches | ThePornDB searches transmit performer names and related media-credit lookups; its service may log requests. TMDB/Wikimedia searches are disabled in v1.0. |

Local users with filesystem access to the installation or backups may read tokens and indexed metadata. Windows filesystem permissions are inherited from the installation location. LAN HTTP traffic is not encrypted; use a trusted network or VPN. **Do not post screenshots or logs containing personal collection details, private IPs, or credentials in public issues.**
