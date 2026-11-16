# Research-driven development

Circle is developed through successive computational experiments. The long-term
architecture is one language with a small computational core, extensible domain
modules, versioned intermediate representations and explicit backend contracts.
The currently shipped cellular profiles are a bounded implementation of that
direction, not a promise that every program runs on every biological substrate.

## After each experiment round

1. Identify reusable implementation lessons: semantics, domain operations,
   backend capabilities, diagnostics, examples, compatibility or documented
   limits. A negative experiment can reveal a useful missing capability.
2. Make the corresponding source or documentation change. Keep empirical
   contract thresholds separate from compiler correctness; do not relax a
   scientific test to manufacture a software success.
3. Run the relevant tests and existing compatibility regressions. For runtime
   or packaging changes, also install a built wheel and run the affected example
   outside the checkout. Report actual environments and outcomes.
4. Update examples, documentation and the changelog. State what is implemented,
   experimental or unsupported, and where program state and transitions execute.
5. Review the diff, commit and push the intended files, then check remote commit
   visibility and triggered CI. Use the repository's branch protection when
   applicable. Record the resulting commit in the research round's provenance.

Use the [round-update template](round-updates/TEMPLATE.md) for substantive
software updates. If no reusable source change follows, a documented limitation
or example can still be useful. If neither source nor public documentation
needs a change, record the existing commit and a no-change reason in the local
research record; empty commits and artificial version bumps are unnecessary.

## Freeze experiments, evolve the implementation

Before an experiment, pin the actual source revision, dependency versions and
backend/model artifact, and retain the source bytes or distribution used. An
experiment must not silently follow a moving development branch. Preserve
historical inputs and failed attempts.

The commit used to generate a result and the commit containing a subsequent
improvement are different provenance fields. A post-result fix is not
retroactively the implementation used in that experiment. Changes to dynamics,
numerical semantics, state access or scoring must be explicit and versioned.

Keep the following claims separate:

| Evidence | What it establishes |
| --- | --- |
| Parser/compiler tests | The implemented language rules and rejection behavior |
| Software regressions | Compatibility on the tested fixtures and environments |
| Finite backend experiments | Execution and conformance on declared model histories |
| Biological or embodied validation | Requires its own applicable evidence |

An external reference state machine is not a neural memory implementation. A
successful finite trace is not a universal guarantee or biological validation.
Unresolved capabilities should be rejected or reported explicitly.

## Commits and releases

Commits are the normal unit of per-round development. A tagged release groups
a coherent, checked milestone. Package versions, language/IR schemas and model
versions have separate compatibility responsibilities: changing a package label
must not silently reinterpret an existing artifact. See [RELEASING.md](../RELEASING.md).

The language repository contains source, tests, small examples and public
documentation. Large simulation archives, private research conversations and
unpublished manuscripts are maintained separately. Imported code and model data
retain their actual licenses; Circle's MIT license does not relicense external
components. A source push is distinct from a package-index upload or paper
submission.
