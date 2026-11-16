# Round <identifier>: <software change>

Copy this template for a substantive update; it is not a completed experiment.

- **Research round:** identifier or public evidence link, where available.
- **Experiment input revision:** actual commit/source snapshot used before execution.
- **Software change:** the implementation lesson and affected core/domain/backend.
- **Supported behavior:** the exact new or corrected capability.
- **Scope and remaining limits:** experimental status, execution location and known failures.
- **Compatibility:** language/schema/backend versions affected and preserved behavior.
- **Validation:** commands, environment and actual test/packaging/CI outcomes.
- **Example:** a small reproducible source program or diagnostic.
- **Provenance and licenses:** origins of new code/data and applicable terms.

Record the resulting publication commit and remote verification in the round's
external provenance receipt after pushing. Avoid putting a commit's own hash
inside a file that is part of that same commit. Do not label post-result changes
as the revision that generated the earlier experiment.
