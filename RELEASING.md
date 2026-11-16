# Release procedure

The public source repository is [mandel0614/circle-lang](https://github.com/mandel0614/circle-lang).
The distribution currently identifies itself as **0.1.0rc1**, a research preview.
A source commit is not a package-index release or a claim of biological validation.

## Per-round development

After each research round, review its implementation lessons, validate relevant
changes, update documentation/examples and synchronize the intended source with
GitHub. Record the actual remote commit and CI status in the research provenance.
See [Research-driven development](docs/research-development.md) and the
[round-update template](docs/round-updates/TEMPLATE.md). Use ordinary commits for
incremental work and tags/releases for checked milestones; no-change rounds do
not require an artificial version bump.

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

## Before a tagged release

- Use the existing `mandel0614/circle-lang` repository. The Python distribution is also named `circle-lang`; a package-index publication is a separate step.
- Include the MIT LICENSE file and the `MIT` SPDX expression in package metadata. The license was selected by the project owner on 2026-09-17.
- Keep citation metadata aligned with the confirmed author and repository; add DOI/arXiv identifiers only when known. The software copyright notice uses `circle-lang contributors`.
- Change preview wording to match the actual release. Register package names only if desired and available; a GitHub source release does not require a package-index upload.
- Publish from this standalone Git checkout only. Preserve any separate source tree or distribution that earlier experiments bind by hash; it is not the mutable development checkout. Parent research workspaces are not release roots.
- Run CI, inspect outcomes, create the version tag and release notes, and attach checked distributions and checksums. Pin the paper to a specific release/commit; obtain an archival DOI if the owner wants one.

Do not transfer historical experimental pass counts to the newly packaged language without the appropriate qualification. The local regression report only demonstrates tested numerical consistency and software behavior. PhysiCell adapters and prospective certification remain separate future releases.

## Release design reference

[Triton's repository](https://github.com/triton-lang/triton) is the structural reference for an approachable README, installation, tutorials, testing, contribution guide, and versioned releases. Circle's research-preview scope and validation are stated independently; no Triton implementation has been reused.
