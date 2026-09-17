# Architecture and provenance

```text
.circle source
  -> tokenizer -> typed AST -> semantic profile validation
  -> versioned BioIR {source, source hash, declarations, behavior, contracts, kernel}
  -> validated artifact loader
  -> runtime configuration resolution and kernel dispatch
  -> empirical metrics + source contract checks + trace + run receipt
  -> optional offline HTML report
```

`language.py` owns the front end and artifact schema. `runtime.py` resolves external scenario bindings and dispatches to kernels. Logical semantics are implemented in the adapter. `_research/` contains the adapted numerical reference code. `cli.py` handles files and exit status. `report.py` embeds actual report data into the bundled report template. No source string is evaluated as Python, and artifacts contain no pickles or executable plugin imports.

The current compiler performs validated template lowering: source structure chooses a supported profile, input names establish bindings, the homeostasis interval parameterizes its controller, and rules parameterize logical execution. It does not run AlphaEvolve, policy search, or model training. Contract thresholds configure evaluation, not controller search. A compile-time selection plus runtime interpreter is a language implementation, but it should not be described as a general-purpose biological compiler.

The shipped numerical provenance manifest records original relative archive paths, original SHA-256 hashes, release-file hashes, and transformations. Adaptations consist of relative imports, extracting relevant constants/functions, removing unused historical CLI/parser dependencies, removing the Numba requirement for cohesion, and inserting observers that receive copies. Fixtures have a separate provenance manifest. Original archives and private research conversations are not required to install or run Circle.

Run receipts record source/artifact/configuration hashes, numerical provenance, a hash of all installed Python implementation files, resolved configuration, seeds, versions, platform, metrics, contract checks, and first-seed trace. These fields support investigation and replay; they are not cryptographic attestations, statistical certificates, or complete dependency lockfiles. Reproducibility should be evaluated with the same release and dependency versions.

## Boundaries of 0.1

- One program per file; no module imports, functions, arbitrary arithmetic, loops, or mixed logical/continuous rules.
- One logical cell or a fixed 64-cell abstract simulation. Population size and horizon are not user parameters.
- Five tested profiles with explicit unsupported-combination errors.
- No published package index entry or reserved distribution/repository name.
- No PhysiCell launch/build integration and no prospective admission/certification command.
- Cohesion uses centralized connected-component means and the transparent CPU reference loop.
- Archives include more extensive research stages than this small executable release exposes. M10 is treated as a consolidation artifact; it does not override source experiment semantics.

The next research-facing extensions should be independently versioned: formal backend contracts and a verified PhysiCell adapter, explicit admission protocols with fresh calibration/holdout data, and additional language composition semantics with evidence that their intended behaviors are actually executable.
