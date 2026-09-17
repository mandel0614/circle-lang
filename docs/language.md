# Circle 0.1 language reference

A file contains one `cell` declaration. Identifiers are ASCII letters or underscores followed by letters, digits, or underscores. Names and keywords are case-sensitive. Comments start with `#`. Numbers support decimal and exponent notation; NaN and infinity are forbidden. Every simple statement and action ends in `;`. A rule ends at its closing brace without a semicolon.

```text
program    = "cell" identifier "{" statement* "}"
statement  = "input" identifier ";"
           | "state" identifier ["in" interval] ";"
           | "maintain" identifier "in" interval ";"
           | "migrate" "toward" identifier ";"
           | "avoid" identifier ";"
           | "budget" number ";"
           | "cohere" ";"
           | "require" identifier comparator number ";"
           | "when" condition ("and" condition)* "{" action+ "}"
condition  = identifier "is" identifier
action     = ("activate" | "deactivate" | "increase" | "decrease") identifier ";"
interval   = "[" number "," number "]"
comparator = ">=" | "<=" | "=="
```

Parsing consumes the entire file. Unknown statements, trailing text, duplicate declarations, unresolved symbols, inappropriate condition values, and unsupported profiles are errors. Syntax errors include line and column. Semantic checks currently report the parser's current location, usually the end of the program.

## Profiles and types

- `input A;` denotes a HIGH/LOW signal in logical programs, or a scalar field binding in navigation/composition programs. The profile determines its type. Field values are supplied by the runtime's Gaussian environments.
- `state X;` is an ACTIVE/INACTIVE state, initialized INACTIVE.
- `state H in [0, 1];` declares the only continuous state. Only this domain is supported.
- `maintain H in [low, high];` requires `0 <= low < high <= 1`. The behavior must use the declared continuous state.
- Navigation requires exactly two distinct inputs, one used by `migrate toward` and the other by `avoid`.
- Composition requires `[0.4, 0.6]` and `budget 0.75`; unsupported values are rejected. Its population and horizon are fixed.
- `cohere;` selects the frozen population kernel and cannot be mixed with other behaviors in 0.1.
- Rules cannot be mixed with continuous or spatial behaviors in 0.1. A source file is not a collection of independently executable cells.

Logical conditions accept HIGH/LOW for inputs and ACTIVE/INACTIVE for states. `activate` and `deactivate` target logical states. `increase` and `decrease` target `motility`, `division`, or `secretion`.

## Contracts

Every `require` is evaluated separately for each seed after execution. It is a requested empirical criterion. It does not tune or retrain the selected controller. Multiple clauses combine with AND. Duplicate clauses for the same metric are rejected in this version. Thresholds must be nonnegative, with fractions and occupancies bounded by one.

| Profile | Accepted metrics |
|---|---|
| Logic | `motility`, `division`, `secretion` |
| Navigation | `target_occupancy`, `forbidden_entry_fraction`, `mean_final_distance` |
| Homeostasis | `band_occupancy`, `unsafe_state_fraction`, `recovery_fraction`, `mean_abs_error` |
| Composition | `target_occupancy`, `forbidden_entry_fraction`, `band_occupancy`, `unsafe_state_fraction`, `recovery_fraction`, `budget_violations`, `mean_final_distance` |
| Cohesion | `giant_component_fraction`, `radius_of_gyration`, `overcrowding_fraction` |

A missing contract is reported as unspecified, not passed. `==` uses exact equality and is appropriate for integer counts such as zero budget violations. There are no implicit aggregate, population-distribution, confidence-interval, or certification constraints. The report also retains the selected kernel's historical per-run task criteria as `research_task_pass`; these are distinct from user-written contracts.

## BioIR

`circle compile source.circle -o program.bioir.json` produces a JSON artifact with the complete source, source SHA-256, canonical program structure, language/schema versions, selected kernel, backend, contract scope, and certification status. It is interpreted by the matching Circle runtime; it is not native machine code. The loader recompiles the embedded source and compares all fields. Edited fields, extra fields, or incompatible versions are rejected. Hashes provide identity and corruption detection; they are not digital signatures.
