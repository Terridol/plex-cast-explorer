# Publication status

**2026-10-14: `dev` v0.4.7-beta is a source/development candidate; no production-validated Windows installer has been published.**

| Area | Status | Notes |
| --- | --- | --- |
| License | **Adopted, unreviewed** | Custom noncommercial network source-share license; no required paid legal review |
| Tests | 42 passed locally (source regression and fail-closed gate tests); Windows EXE/installer integration pending | Synthetic tests; live provider integration unverified |
| Secrets/runtime files | Excluded from source archive | Recheck every Git commit and distribution |
| Contributor rights | Pending workflow | Do not merge external copyrighted contributions without permission sufficient for commercial exceptions |
| Third-party providers | **Not fully verified** | Confirm trademark attribution, cache policy, and permitted use |
| Security | **Not independently audited** | HTTP LAN service; no WAN exposure |
| Windows + Linux smoke tests | Pending | Clean installation and live providers |
| GitHub-hosted execution | **Prohibited by maintainer** | Do not enable Actions/CI. Local build gates only; main still has an older workflow trigger. |

**License notice:** The owner chose to publish without buying legal review. This is a custom, non-OSI license; its enforceability has not been independently evaluated. This is not a legal or industry-compliance certification.

**Release principle:** Publishing development source does not automatically mean a tagged stable release is ready. For releases, complete the remaining engineering and provider checks described in [RELEASE.md](RELEASE.md).

## Installer preview

The `dev` branch includes the source for a Windows Inno Setup installer with upgrade preservation and an on-demand update checker. Source checks passed locally; real Windows EXE build-gate, firewall verification, clean install, in-place upgrade, and reboot testing remain pending. Do not call this a production-validated release.
