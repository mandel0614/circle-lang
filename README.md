# Circle

**A declarative programming language for virtual cells.**

Circle lets you describe **what a virtual cell should do**, rather than how a
particular simulator should implement it.

A Circle program is parsed into versioned **BioIR**, lowered to an executable
runtime profile, executed on virtual-cell populations, and checked against
phenotype-level contracts.

```text
Circle source
     │
     ▼
   BioIR
     │
     ▼
runtime lowering
     │
     ▼
virtual-cell execution
     │
     ▼
phenotype verification
````

> **Status:** `0.1.0rc1` · research preview · MIT licensed

The project and Python distribution are named `circle-lang`.
The language is **Circle**, the Python package is `circle_lang`, and the
command-line executable is `circle`.

---

## A first Circle program

```circle
cell Explorer {
  input A;
  input B;

  state X;

  when A is HIGH and B is LOW {
    activate X;
  }

  when X is ACTIVE {
    increase motility;
  }

  require motility >= 2;
}
```

With `A=HIGH` and `B=LOW`, `X` becomes active and the abstract motility state
reaches `2`.

Circle separates three concerns:

* **behavior specification** — what cells should sense and do;
* **runtime realization** — how those behaviors are executed;
* **phenotype contracts** — what observable outcomes must hold.

The example above operates on an abstract intracellular state. Circle also
supports executable spatial and multicellular profiles.

---

## Installation

Circle requires **Python 3.10+** and **NumPy**.

No GPU, web service, or external simulator is required for the default CPU
runtime.

```bash
python3 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install .
circle --version
```

---

## Quick start

Check a source program:

```bash
circle check examples/00_hello_cell.circle
```

Compile it to BioIR:

```bash
circle compile examples/00_hello_cell.circle \
  -o runs/explorer.bioir.json
```

Execute and verify it against a scenario:

```bash
circle verify runs/explorer.bioir.json \
  --config examples/00_signals.json \
  -o runs/explorer.json \
  --html runs/explorer.html
```

The resulting receipt records:

* resolved program and runtime configuration;
* seeds and execution parameters;
* observed phenotype metrics;
* contract results;
* code and configuration provenance.

The generated HTML report is self-contained and can be opened locally without
a network connection.

---

## Spatial behavior

Circle can also describe a moving cell population:

```circle
cell Navigator {
  input attractant;
  input hazard;

  migrate toward attractant;
  avoid hazard;

  require target_occupancy >= 0.80;
  require forbidden_entry_fraction <= 0.10;
}
```

Run five stochastic executions:

```bash
circle run examples/01_navigation.circle \
  --seeds 0:5 \
  -o runs/navigation.json \
  --html runs/navigation.html
```

`0:5` denotes seeds `0, 1, 2, 3, 4`.

For the current navigation profile, Circle executes a population of 64 virtual
cells for 190 ticks using the frozen navigation kernel associated with the
research implementation.

The HTML report visualizes one execution trace, while the JSON receipt records
metrics for every seed.

Compilation guarantees that the program can be lowered to the selected runtime
profile. It does **not** guarantee that stochastic execution will satisfy every
phenotype contract.

---

## Language model

Circle programs describe biological behavior using a small set of declarative
constructs.

Examples include:

```circle
migrate toward attractant;
avoid hazard;

maintain internal_state near 0.5;

cohere with neighbors;

require target_occupancy >= 0.80;
require overcrowding_fraction <= 0.10;
```

The language is intentionally separated from simulator-specific APIs.

A source-level behavior is first represented in **BioIR** and only then lowered
to a concrete execution profile.

```text
behavioral intent
       │
       ▼
   Circle AST
       │
       ▼
     BioIR
       │
       ├────────► abstract CPU runtime
       │
       └────────► future simulator backends
```

This distinction is fundamental: runtime operations with similar names are not
assumed to have equivalent semantics.

---

## BioIR

BioIR is Circle's versioned intermediate representation for executable
biological behavior.

It records, among other information:

* declared inputs and state;
* behavioral operators;
* phenotype contracts;
* runtime requirements;
* composition parameters;
* lowering metadata;
* provenance information.

BioIR provides the boundary between the language frontend and runtime-specific
implementations.

```bash
circle compile program.circle -o program.bioir.json
```

BioIR is designed to be inspectable and serializable rather than hidden inside
the compiler.

---

## Supported execution profiles

Circle `0.1` intentionally supports a finite set of research-backed execution
profiles.

| Profile         | Circle constructs                          | Execution model                                               | Research lineage           |
| --------------- | ------------------------------------------ | ------------------------------------------------------------- | -------------------------- |
| **Logic**       | `when`, `activate`, `increase`, ...        | One abstract logical cell; synchronous fixed-point evaluation | M0.5                       |
| **Navigation**  | `migrate toward`, `avoid`                  | 64 cells; 190 ticks; normalized 2D domain                     | M8.6 abstract R1           |
| **Homeostasis** | `maintain`                                 | 64 independent continuous states; 200 ticks                   | M6.3                       |
| **Composition** | Navigation + homeostasis + resource budget | 64 cells; 200 ticks; shared per-cell resource allocation      | M7.18 frozen v3            |
| **Cohesion**    | `cohere`                                   | 64 locally interacting cells; 220 ticks                       | M9.12 / frozen M9.6 kernel |

Circle `0.1` is therefore **not** an unrestricted biological-program synthesis
system.

Unsupported syntax, runtime profiles, behavior combinations, or composition
parameters are rejected explicitly rather than silently approximated.

---

## Composition

Multiple behaviors may compete for shared execution resources.

Circle exposes this explicitly rather than assuming that independently valid
programs can always be combined.

A composition may therefore require:

```text
behavior compatibility
        +
resource analysis
        +
capacity analysis
        +
admission
```

The current composition profile is derived from the frozen resource-aware
linking and uncertainty-aware admission implementation used in the associated
research program.

See [Execution semantics](docs/semantics.md) for the exact model.

---

## Verification

Circle distinguishes **execution** from **verification**.

```bash
circle run program.circle
```

executes a valid program.

```bash
circle verify program.circle
```

executes the program and evaluates every declared phenotype contract.

Exit codes are:

| Code | Meaning                                                         |
| ---: | --------------------------------------------------------------- |
|  `0` | Every evaluated contract passed                                 |
|  `1` | Execution completed, but at least one empirical contract failed |
|  `2` | Invalid input, compilation failure, or execution error          |

A program without contracts may be executed but cannot establish a phenotype
verification result.

Circle does not issue formal biological certificates. Verification results are
empirical outcomes of the specified computational execution.

---

## Reproducibility

Circle execution receipts are intended to make computational results auditable.

A receipt may include:

```text
source program
compiler version
BioIR version
runtime profile
resolved configuration
random seed
execution metrics
contract results
code provenance
```

Regression fixtures are used to detect unintended changes to frozen execution
profiles.

```bash
python -m unittest discover -s tests -v
```

See [Validation](docs/validation.md) for the exact reproducibility guarantees
and their limitations.

---

## Documentation

Start here:

* **[Tutorials](docs/tutorials.md)**
  Executable examples covering logic, navigation, homeostasis, composition,
  and collective cohesion.

* **[Language reference](docs/language.md)**
  Grammar, declarations, behaviors, contracts, symbols, and diagnostics.

* **[Execution semantics](docs/semantics.md)**
  Runtime equations, sampling rules, metrics, fixed parameters, and known
  limitations.

* **[Architecture and provenance](docs/architecture.md)**
  Circle source → BioIR → runtime lowering → execution evidence.

* **[Validation](docs/validation.md)**
  Regression fixtures, frozen research kernels, and reproducibility scope.

* **[Release procedure](RELEASING.md)**
  Release-candidate, repository, package, and versioning workflow.

---

## Project structure

```text
circle-lang/
├── circle_lang/
│   ├── frontend/
│   ├── bioir/
│   ├── lowering/
│   ├── runtimes/
│   ├── verification/
│   └── cli.py
│
├── examples/
├── docs/
├── tests/
├── pyproject.toml
├── LICENSE
└── README.md
```

The major compiler stages are:

```text
source
  ↓
lexer / parser
  ↓
AST
  ↓
semantic analysis
  ↓
BioIR
  ↓
profile selection
  ↓
runtime lowering
  ↓
execution
  ↓
phenotype verification
```

---

## Research scope

Circle `0.1` is a **research programming language for virtual-cell systems**.

The current release covers computational abstractions at three levels:

* intracellular abstract state;
* cell migration;
* multicellular interaction.

It does **not** provide:

* molecular or biochemical mechanism inference;
* genome or DNA design;
* CRISPR design;
* wet-lab execution;
* experimental biological validation;
* therapeutic prediction;
* arbitrary tissue programming.

The associated research program also contains transfer experiments using
PhysiCell. Circle `0.1` currently distributes only the abstract CPU execution
profiles.

Passing Circle's software tests therefore demonstrates software regression
consistency. It does not constitute a repeat of the complete research study,
a new blind validation experiment, or experimental biological evidence.

---

## Research provenance

Circle `0.1` consolidates syntax and runtime interfaces around a set of frozen
research implementations developed before the public language release.

The unified Circle syntax is new engineering work.

Accordingly, Circle `0.1` should **not** be described as the exact software
interface used to generate every historical experiment. Instead, the release
provides a common language and compiler frontend over research-backed execution
profiles whose provenance is documented individually.

See:

* [Architecture and provenance](docs/architecture.md)
* [Validation](docs/validation.md)

---

## Development

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

Check the CLI:

```bash
circle --help
circle --version
```

Run all examples:

```bash
circle check examples/00_hello_cell.circle
circle run examples/01_navigation.circle
```

Development contributions should preserve:

1. explicit semantics;
2. deterministic compilation;
3. versioned BioIR;
4. reproducible execution receipts;
5. explicit errors for unsupported behavior;
6. separation between language semantics and runtime-specific implementation.

---

## Versioning

Circle uses semantic versioning for the language distribution.

During the `0.x` research-preview series, syntax and BioIR may evolve between
minor versions.

BioIR documents include an explicit schema version so that incompatible
changes can be detected rather than silently interpreted.

Current candidate:

```text
Circle           0.1.0rc1
Package          circle-lang
Python module    circle_lang
CLI              circle
License          MIT
```

---

## Citation

If you use Circle in research, please cite the accompanying LifeCompiler
manuscript.

Formal citation metadata, the permanent repository URL, and the arXiv
identifier will be added with the public release.

A `CITATION.cff` file will be included in the tagged release.

---

## License

Circle is released under the [MIT License](LICENSE).

Copyright © Circle contributors.

````
