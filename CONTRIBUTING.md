# Contributing

Bug reports, discussion, and documentation feedback are welcome. **External copyrighted code contributions will not be merged until a contributor-rights workflow is finalized**. This project is source-available under a custom noncommercial, network-source-sharing license, not OSI-approved open source. Do not assume that opening a pull request conveys commercial-relicensing rights.

1. Search existing issues first; for significant features, open an issue describing the proposed behavior.
2. Fork the repository or create a feature branch. Keep each pull request focused, with a clear rationale and tests for changed behavior.
3. Use Python 3.10-compatible standard-library code unless a dependency is justified and documented. Keep the app usable on Windows.
4. Run `python -m unittest discover -s . -p 'test_*.py' -v` and `python -m compileall -q app.py manage.py` before submitting.
5. Document changes affecting install, configuration, user workflows, security, providers, or data formats. Add a changelog entry for user-visible changes.
6. Never post or commit Plex tokens, external API keys, personal library data, portrait cache files, credentials, or unredacted logs. Use synthetic test data.
7. Only submit code, text, or artwork that you are authorized to contribute, and disclose third-party license requirements. All accepted Program-derived contributions must be distributable under the custom project license. The maintainer also intends to request a separate [Contributor License Agreement](legal/CONTRIBUTOR_LICENSE_AGREEMENT_PROPOSAL.md) permitting the maintainer to grant commercial exceptions while contributors retain copyright. **Until a signed CLA workflow is established, maintainer should not merge third-party copyrighted contributions.**

Maintainers review changes for correctness, cross-platform behavior, testing, security, privacy, accessibility, and documentation. Pull requests may be declined or revised; passing CI does not guarantee acceptance. Use issues for bugs and feature requests, and private security reporting for vulnerabilities.
