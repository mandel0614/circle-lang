# Validation of the 0.1.0rc1 local candidate

The local suite passes **26 test methods**, including parameterized numerical comparisons for **662 archived simulation runs**. Tested environment: macOS arm64, Python 3.12.14, NumPy 2.3.5. The precise installed Python version is also recorded in generated receipts. See `local-test-results.txt` for the test log and `local-validation.json` for release checks.

| Regression group | Coverage | Comparison |
|---|---|---|
| M8.6 navigation | All 12 archived worlds, seed 29000 | Occupancy, exposure, endpoint distance, task outcome |
| M7.18 composition | All 48 world/disturbance pairs, seed 25000 | Phenotype metrics, allocation counters, risk debt, joint outcome |
| M6.3 homeostasis | Two contexts × six scenarios × 50 seeds = 600 runs | Archived scenario means and task pass rates |
| M9.12 cohesion | One frozen geometry, seed 35000, interaction and control = 2 runs | Connectivity, radius, overcrowding |

Navigation and homeostasis comparisons use 11 decimal places, composition uses 10, and rounded archived cohesion results use 9. These tolerances reflect saved output precision and floating-point evaluation. Homeostasis fixtures preserve archived aggregate results rather than inventing individual historical rows. All 600 constituent runs are re-executed to obtain those means.

Other tests cover complete parsing, syntax diagnostics, semantic rejection, finite inputs, symbol/type errors, frozen composition boundaries, synchronous rules, conflict/non-convergence errors, source mutation changing execution, contracts leaving controllers unchanged, deterministic replay, trace observers leaving results unchanged, batched composition matching individual seeds, artifact tampering, seed validation, CLI exit status, input/output collision rejection, duplicate JSON keys, and inert HTML data embedding.

Five demonstrations execute all source contracts successfully for their listed seeds. The explicit no-interaction cohesion control completes and fails the requested cohesion contract, demonstrating that failure is retained in the report. These are demonstrations, not a success-rate estimate. `tools/run_examples.py` regenerates all six receipts and reports with declared scenarios and seeds.

The wheel is installed into a separate temporary virtual environment and exercised from outside the checkout. This environment reuses the preinstalled NumPy dependency through system site packages; it is an isolated package installation, not a fresh dependency download. The source archive is separately unpacked for installation and validation. CI is configured for Linux/macOS/Windows and Python 3.10/3.12/3.13, but those remote jobs have not run and are not claimed as passed.

The HTML report has been inspected in the local browser, with the time slider checked through the final tick. It displays recorded trajectories/state values, contract results, source code, and configuration; it does not rerun the model in JavaScript.

## Limits of this evidence

The 662 runs are intentionally reused regression data, not held-out validation. Cohesion regression covers a single archived fixed geometry and its control; it does not rerun the full M9.12 benchmark. This suite does not execute PhysiCell, replay all M0–M10 experiments, run prospective certification, or support any claim of biological validity. Versioned fixtures and provenance make software changes reviewable; broader scientific claims remain governed by the original experiment definitions and manuscript evidence.
