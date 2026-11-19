<div align="center">

# Circle

**A research language for programmable biological systems.**

High-level behavior specifications → executable models → measurable outcomes.

[![Validation](https://github.com/mandel0614/circle-lang/actions/workflows/ci.yml/badge.svg)](https://github.com/mandel0614/circle-lang/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![MIT License](https://img.shields.io/badge/license-MIT-5B6D53)](LICENSE)

[Get started](#get-started) · [Language guide](docs/language.md) · [Examples](examples) · [Development](#developing-circle)

</div>

Circle explores **life programming**: expressing intended behavior as a program,
compiling it for an explicit biological model, and measuring what that model
actually does.

The current **0.1.0rc1 research preview** implements five abstract virtual-cell
profiles. It provides a small declarative language, an inspectable intermediate
representation, CPU simulation runtimes, and reports that connect source code
to observed behavior. Neural and embodied execution are research directions for
the evolving language.

## A first program

Declare the signals, specify a response, and state a measurable requirement:

```text
cell Explorer {
  input A;
  input B;
  state X;

  when A is HIGH and B is LOW { activate X; }
  when X is ACTIVE { increase motility; }

  require motility >= 2;
}
```

With `A = HIGH` and `B = LOW`, the logical runtime activates `X` and sets the
abstract motility level to `2`. The `require` clause checks the result; it does
not train or optimize a controller to make the requirement pass.

## Get started

Circle requires **Python 3.10+** and NumPy. Install from this repository:

```bash
git clone https://github.com/mandel0614/circle-lang.git
cd circle-lang
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

On Windows, create the environment with `python -m venv .venv` and activate it
with `.venv\Scripts\Activate.ps1` in PowerShell.

Compile the example into **BioIR**, then execute it with the supplied signals:

```bash
circle check examples/00_hello_cell.circle
circle compile examples/00_hello_cell.circle -o runs/explorer.bioir.json
circle verify runs/explorer.bioir.json \
  --config examples/00_signals.json \
  -o runs/explorer.json --html runs/explorer.html
```

Open `runs/explorer.html` in a browser to inspect the execution. All reports work
offline; output directories are created automatically.

| Artifact | What it contains |
| :--- | :--- |
| `explorer.bioir.json` | Source, declarations, selected profile, contracts, and source hash |
| `explorer.json` | Results, contract checks, execution trace, and run provenance |
| `explorer.html` | A visual view of the recorded execution and its evidence |

The CLI also accepts `.circle` source directly. To generate all five profile
demonstrations and the cohesion control, run `python tools/run_examples.py`,
then open `runs/index.html`.

## From signals to spatial behavior

The same language can describe a spatial objective:

```text
cell Navigator {
  input attractant;
  input hazard;

  migrate toward attractant;
  avoid hazard;

  require target_occupancy >= 0.80;
  require forbidden_entry_fraction <= 0.10;
}
```

```bash
circle run examples/01_navigation.circle --seeds 0:5 \
  -o runs/navigation.json --html runs/navigation.html
```

This executes seeds `0` through `4`. The HTML report displays the first seed's
recorded trajectory alongside results for every seed.

## What runs today

| Profile | Program intent | Example |
| :--- | :--- | :--- |
| **Logic** | Respond to signals through synchronous state rules | [Signal-driven cell](examples/00_hello_cell.circle) |
| **Navigation** | Move toward an attractant while avoiding a hazard | [Navigation](examples/01_navigation.circle) |
| **Homeostasis** | Keep an internal state within a declared interval | [Homeostasis](examples/02_homeostasis.circle) |
| **Composition** | Combine navigation and homeostasis under a fixed shared budget | [Composition](examples/03_composition.circle) |
| **Cohesion** | Maintain group connectivity through interactions | [Cohesion](examples/04_cohesion.circle) |

These profiles use validated template lowering: the compiler maps supported
source constructs to versioned reference kernels. Logic executes one abstract
cell; the numerical profiles execute fixed 64-cell simulations. Unsupported
syntax and profile combinations produce explicit errors. Cohesion includes
centralized connected-component calculations.

See the [language guide](docs/language.md) for accepted syntax and the
[semantics](docs/semantics.md) for each profile's assumptions and limits.

## From source to evidence

```text
.circle source
      │
      ▼
Parse & validate ──► BioIR ──► Runtime + scenario + seeds
                                       │
                                       ▼
                              Metrics & contract checks
                                       │
                                       ▼
                              JSON receipt + HTML report
```

**Compilation** validates a program and produces an inspectable artifact.
**Execution** runs the selected model. **Contract checks** compare measured
results with the requirements in the source.

Both `circle run` and `circle verify` record contract outcomes. Use `verify`
when those outcomes should control a script or CI job:

| `circle verify` exit code | Meaning |
| :--- | :--- |
| `0` | All requested contracts passed for the executed runs |
| `1` | Execution completed, but at least one contract failed |
| `2` | Invalid input or an execution error |

Run receipts retain source, artifact, configuration and implementation hashes,
resolved settings, seeds, software versions, metrics, and a first-seed trace.
They support replay and inspection. A passing finite simulation is empirical
evidence under its declared conditions, not formal certification or biological
validation.

## Documentation

| Guide | Start here for |
| :--- | :--- |
| [Tutorials](docs/tutorials.md) | Running and interpreting the examples |
| [Language](docs/language.md) | Syntax, declarations, behaviors, and contracts |
| [Semantics](docs/semantics.md) | Logical rules and numerical profile definitions |
| [Architecture](docs/architecture.md) | Compiler, BioIR, runtimes, and provenance |
| [Validation](docs/validation.md) | Regression coverage and evidence boundaries |
| [Research-driven development](docs/research-development.md) | How experiments inform the language |

## Developing Circle

The architectural direction is **a small computational core, extensible
biological domain types, layered intermediate representations, and multiple
backends**. The cellular implementation is the starting point. Research on
stateful neural programs and embodied virtual organisms will inform future
semantics and backends as their execution capabilities are established.

Each research round feeds reusable changes back into source, tests, examples,
or documentation. Experiments preserve the exact implementation they used;
later improvements receive their own commits. See the
[development workflow](docs/research-development.md) and
[round-update template](docs/round-updates/TEMPLATE.md).

For a development installation:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

The implementation lives in [`src/circle_lang`](src/circle_lang):
`language.py` handles parsing and compilation, `runtime.py` dispatches execution,
`report.py` renders reports, and `_research/` contains the adapted reference
kernels. Contributions are welcome through
[issues](https://github.com/mandel0614/circle-lang/issues) and pull requests.
Read [CONTRIBUTING.md](CONTRIBUTING.md) before changing numerical semantics;
release procedures are in [RELEASING.md](RELEASING.md).

## Research and citation

Circle accompanies the research manuscript by **Mandel**:

When referring to the software, cite this
[repository](https://github.com/mandel0614/circle-lang) with the exact commit
or release used. For computational results, also record the runtime profile,
configuration, seeds, and dependency versions.

## License

Circle is released under the [MIT License](LICENSE). External code, models,
and datasets retain their respective licenses and attribution requirements.
