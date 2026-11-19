# Cross-platform validation status

The full CI matrix at commit `6d1d6fa65cb53d8fd25a4f8def54ac11cbb66221`
completed on 19 November 2026. The [diagnostic run](https://github.com/mandel0614/circle-lang/actions/runs/44437839226)
preserves the original regression assertions and publishes failure details in
job annotations.

| Runner | Python versions | Observed result |
| --- | --- | --- |
| macOS | 3.10, 3.12, 3.13 | All 26 test methods, CLI smoke check and wheel build passed |
| Ubuntu | 3.10, 3.12, 3.13 | 25 test methods passed; frozen cohesion regression failed |
| Windows | 3.10, 3.12, 3.13 | 24 test methods passed; frozen cohesion and source-integrity regressions failed |

These observations describe this particular run, not every platform or future
dependency version. The source-integrity and numerical failures are separate
issues.

## Checkout bytes

Windows converted a vendored Python file to CRLF line endings. For
`_research/compiler_m77.py`, the recorded LF SHA-256 starts with `1b6cec6b3545`;
converting those same bytes to CRLF produces `158d68df462c`, exactly matching
the failing Windows annotation. This explains the integrity failure without
implying that the recorded source was changed intentionally.

The repository now declares `* text=auto eol=lf` in `.gitattributes` to preserve
text bytes during checkout, including when Git has `core.autocrlf=true`.
The source-integrity test and its recorded hashes remain unchanged. Subsequent
CI runs must verify the fix on Windows; the table above is the pre-fix record.

## Frozen cohesion regression

The first failing cohesion comparison is the radius of gyration:

| Result | Radius of gyration |
| --- | --- |
| Archived fixture | 0.1464638121 |
| Ubuntu diagnostic run | 0.1467515510366078 |
| Windows diagnostic run | 0.1466387539050984 |

The differences exceed the existing nine-decimal-place regression tolerance.
Their numerical cause has not yet been isolated. The kernel has threshold-based
neighbor and component decisions, so propagation of small math-library
differences is a hypothesis to test, not an established diagnosis.

The frozen kernel, fixture values and assertions are retained. Cross-platform
reproduction of this fixture remains unresolved; a successful run on macOS
does not establish numerical portability. A future resolution needs controlled
trajectory comparisons and an explicit compatibility decision if numerical
semantics change. It must not substitute new expected values merely to make
the current CI pass.

See [validation](validation.md) for the original reference evidence and
[GitHub Actions](https://github.com/mandel0614/circle-lang/actions/workflows/ci.yml)
for results tied to later commits.
