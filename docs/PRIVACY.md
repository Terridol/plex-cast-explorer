# Privacy and local data

Plex Cast Explorer is self-hosted. The code does not include a cloud account or telemetry collector.

| Data | Where it lives or goes |
| --- | --- |
| Plex URL and token | Server-side `config.json`; sent to your configured Plex server. |
| Gallery password verifier/session signing secret | Server-side `auth.json`; never store a plaintext password. |
| Artwork provider credentials | Server-side `artwork_config.json` (or environment overrides). TMDB and ThePornDB tokens are sent only to their respective APIs when those providers are enabled and used. A saved TMDB token alone does not activate the provider. |
| Movie/show titles, actors, credits, and review decisions | Local `cast_explorer.db`. |
| Downloaded portrait overrides | Local `portraits/`; not distributed with source. |
| Plex actor portrait cache | Local `plex-portraits/`; images fetched from the user's Plex server or Plex-approved image hosts during sync. The cache is not bundled or committed to the public repository. |
| Optional artwork searches | When explicitly enabled, TMDB searches transmit performer names and may retrieve filmography credits; ThePornDB fallback searches transmit performer names and related credit lookups. These services can log requests. Wikimedia remains disabled in v1.0. |

Local users with filesystem access to the installation or backups may read tokens and indexed metadata. Windows filesystem permissions are inherited from the installation location. LAN HTTP traffic is not encrypted; use a trusted network or VPN. **Do not post screenshots or logs containing personal collection details, private IPs, or credentials in public issues.**
