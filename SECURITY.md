# Security policy

## Current status

No public release is supported yet. The pre-release application was developed for use on a trusted local network and has not undergone an independent penetration test.

## Reporting

Please **do not** report vulnerabilities by posting sensitive server details, credentials, or exploit code in public issues. Once GitHub private vulnerability reporting is enabled, use **Security → Report a vulnerability**.

## Network exposure

Do not expose the application's HTTP port to the public Internet or create a WAN port forward. Use a private LAN or a properly secured VPN, and a TLS reverse proxy if remote access is required.

## Secrets

Never commit API tokens, Plex credentials, gallery passwords, configuration with secrets, user indexes, or downloaded portraits. Rotate anything accidentally exposed. Deleting a secret from a later commit does not erase Git history.

## Security expectations

See [beta release readiness checklist](docs/BETA_RELEASE_CHECKLIST.md) for remaining reviews. There is no security certification or guaranteed vulnerability response SLA.
