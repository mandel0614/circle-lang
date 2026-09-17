# Release procedure

The current artifact is **0.1.0rc1, a local release candidate**. The intended sequence is Circle public release, manuscript finalization with the real repository URL and author metadata, then arXiv submission. This document does not authorize or claim any of those external actions occurred.

## Candidate checks

1. Install into a clean environment from the built wheel; ensure it runs outside the checkout.
2. Run `python -m unittest discover -s tests -v` and the five example programs. Record environment, validation outputs, and SHA-256 checksums.
3. Inspect the HTML reports, including a failing contract/control. Check that packaging contains no private chat, manuscript draft, credentials, or unrelated experimental outputs.
4. Review numerical provenance, scientific boundaries, README commands, and required backend dependencies.

Standard build command, after installing the `build` development tool:

```bash
python -m build
```

The package also builds with `python -m pip wheel --no-deps . -w dist` and setuptools' PEP 517 backend. A source distribution should include examples, documentation, regression tests/fixtures, and the MIT LICENSE file. Wheels include executable modules, kernels, scenario manifests, provenance, and report template.

## Before public publication

- Confirm the GitHub owner/organization for the repository named `circle-lang`. The Python distribution is also named `circle-lang`; package-index availability has not been established.
- Include the MIT LICENSE file and the `MIT` SPDX expression in package metadata. The license was selected by the project owner on 2026-09-17.
- Confirm manuscript author names for CITATION.cff and add the permanent repository URL; add DOI/arXiv identifiers only after they exist. The software copyright notice uses `circle-lang contributors`.
- Change preview wording to match the actual release. Register package names only if desired and available; a GitHub source release does not require a package-index upload.
- Initialize and inspect the standalone repository rooted at `circle/`, then publish that directory only. The parent workspace contains private research material and is not a release root.
- Run CI, inspect outcomes, create the version tag and release notes, and attach checked distributions and checksums. Pin the paper to a specific release/commit; obtain an archival DOI if the owner wants one.

Do not transfer historical experimental pass counts to the newly packaged language without the appropriate qualification. The local regression report only demonstrates tested numerical consistency and software behavior. PhysiCell adapters and prospective certification remain separate future releases.

## Release design reference

[Triton's repository](https://github.com/triton-lang/triton) is the structural reference for an approachable README, installation, tutorials, testing, contribution guide, and versioned releases. Circle's research-preview scope and validation are stated independently; no Triton implementation has been reused.
