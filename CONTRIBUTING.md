# Contributing

Plex Cast Explorer is publicly readable **source-available** software under a custom noncommercial source-share license; it is not OSI-approved open source. The owner currently accepts issues, reproducible bug reports, and documentation feedback. **Outside copyrighted code or artwork is not accepted until a suitable contributor-rights process is in place.** Opening a pull request does not grant commercial licensing rights.

## Local development

Use the existing `dev` branch of [Terridol/plex-cast-explorer](https://github.com/Terridol/plex-cast-explorer). The maintainer works directly on `dev` and approves any promotion to `main`; new branches and PRs are not part of the maintainer's current workflow.

The Windows entry point is `BUILD-INSTALLER.cmd`. This runs the PowerShell parser, Python tests, regression mutation tests, compiled EXE smoke test, Inno Setup build, and installer checksum validation **on your Windows computer**. Independent source tests: `python -m unittest discover -s . -p "test_*.py" -v`.

Do not run GitHub Actions, hosted CI, or cloud build/deployment jobs. Do not commit `dist/`, `output/`, `build/`, `installer-assets/`, Plex or provider tokens, passwords, library metadata, private portrait files or logs.

Changes to authentication, provider rights, service upgrades, firewall rules, or the installer require appropriate regression tests and documentation updates. A green source build does not prove that a Windows service upgrade worked; the public release checklist requires a disposable Windows VM test.

See [LICENSE](LICENSE), [project licensing](docs/LICENSING.md), and [existing contributor restrictions](docs/LICENSING.md) for legal limitations. Security reports follow [SECURITY.md](SECURITY.md).

## Maintainer and contributor policy

The repository owner and sole release maintainer is [@Terridol](https://github.com/Terridol). The owner controls releases, write permissions, secret handling, acceptance of outside submissions, and promotion from `dev` to `main`. There are no additional maintainers with release rights presently documented. Use GitHub issues for proposed features and bugs; do not assume unsolicited pull requests or patches will be merged. Commercial exceptions may require grants from all relevant copyright holders; read the [licensing terms](docs/LICENSING.md) and [contribution restrictions](docs/LICENSING.md).
