# Publication status

**2026-10-14: v0.4.2 public source development build; not a production-ready release.**

| Area | Status | Notes |
| --- | --- | --- |
| License | **Adopted, unreviewed** | Custom noncommercial network source-share license; no required paid legal review |
| Tests | 21 passed locally | Synthetic tests; live provider integration unverified |
| Secrets/runtime files | Excluded from source archive | Recheck every Git commit and distribution |
| Contributor rights | Pending workflow | Do not merge external copyrighted contributions without permission sufficient for commercial exceptions |
| Third-party providers | **Not fully verified** | Confirm trademark attribution, cache policy, and permitted use |
| Security | **Not independently audited** | HTTP LAN service; no WAN exposure |
| Windows + Linux smoke tests | Pending | Clean installation and live providers |
| GitHub CI / branch protections | Pending | Configure after source upload |

**License notice:** The owner chose to publish without buying legal review. This is a custom, non-OSI license; its enforceability has not been independently evaluated. This is not a legal or industry-compliance certification.

**Release principle:** Publishing development source does not automatically mean a tagged stable release is ready. For releases, complete the remaining engineering and provider checks described in [RELEASE.md](RELEASE.md).

## Installer preview

The `dev` branch includes the source for a Windows Inno Setup installer with upgrade preservation and an on-demand update checker. Windows compilation, firewall verification and in-place upgrade testing are pending. Do not call this a production-validated release.
