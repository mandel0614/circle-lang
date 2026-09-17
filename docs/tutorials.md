# Tutorials

Run commands from the repository root after installation. All scenarios are observed research or demonstration cases; running them does not create new blind evidence.

## 00 — A first life program

```bash
circle run examples/00_hello_cell.circle --config examples/00_signals.json \
  -o runs/hello.json --html runs/hello.html
```

The first rule activates X; the second increases motility after the state rules converge. Remove the configuration to use LOW for both inputs. Motility remains 1 and the `motility >= 2` contract fails. `run` still completes; `verify` exposes the failure through exit code 1.

## 01 — Move toward a target while avoiding a hazard

```bash
circle scenarios
circle run examples/01_navigation.circle --seeds 0:10 \
  -o runs/navigation.json --html runs/navigation.html
```

The default is the first archived M8.6 world, selected without phenotype screening by Circle. To bind your own fields, save this as `world.json`:

```json
{
  "fields": {
    "attractant": [0.92, 0.50, 0.64],
    "hazard": [0.58, 0.45, 0.13]
  },
  "noise": 0.02
}
```

Each field is `[center_x, center_y, sigma]`; names must match the two source inputs. Coordinates are in `[0,1]` for standalone navigation and `[0,100]` for composition. Noise uses the corresponding coordinate units per tick. Supply `--config world.json`. Alternatively use `{"world":"m86_blind_01"}` with a name from `circle scenarios`; `world` and `fields` are mutually exclusive. A noise value overrides the chosen world's noise. If custom fields omit noise, the first bundled world's noise is retained and fully recorded in the resolved configuration.

## 02 — Maintain an internal state across calibrated runtimes

```bash
circle run examples/02_homeostasis.circle --config examples/02_calibrated_runtime.json \
  --seeds 0:5 -o runs/homeostasis.json --html runs/homeostasis.html
```

The configuration changes sensor gain/offset, actuator efficiency, and disturbance/noise multipliers. The compiler's lowering recalibrates observations and adjusts the internal trigger band. The requested phenotype interval remains the source interval. All context parameters must be finite; every multiplier except the offset must be positive. Source interval changes alter both control and occupancy measurement. The natural relaxation point, unsafe-state bounds, and archived `mean_abs_error` reference remain 0.5, [0.15,0.85], and 0.5 respectively.

## 03 — Compose behaviors under a shared budget

```bash
circle run examples/03_composition.circle --seeds 0:5 \
  -o runs/composition.json --html runs/composition.html
```

The frozen v3 linker allocates a normalized budget of 0.75 per cell per tick between target movement, avoidance, and state control. A configuration may select `world` and `disturbance` identifiers listed by `circle scenarios`. The example's per-run contract requires zero budget violations. Some observed world/disturbance combinations fail phenotype criteria; the implementation reports those failures without substituting another scenario. Empirical success does not confer an M7.18 admission certificate.

## 04 — Observe an interacting colony and its control

```bash
circle run examples/04_cohesion.circle -o runs/cohesion.json --html runs/cohesion.html
circle run examples/04_cohesion.circle --config examples/04_repulsion_control.json \
  -o runs/control.json --html runs/control.html
```

`interaction=false` removes the cohesion components and retains mandatory short-range repulsion. This is a defined control experiment, so a cohesion contract may fail. Geometries include `uniform_cloud`, `bimodal_horizontal`, `bimodal_diagonal`, `ring`, and `boundary_biased`. The pure Python/NumPy reference implementation favors transparent numerical lineage over speed.

## Python API

```python
from pathlib import Path
from circle_lang import compile_source, run

artifact = compile_source(Path("examples/01_navigation.circle").read_text())
report = run(artifact, seeds=[0, 1, 2], trace=True)
print(report["summary"])
```

The default trace includes every tick for the first seed only, including tick 0. `trace=False` removes snapshots without changing simulation metrics. Distinct nonnegative 32-bit integer seeds are required. Repeated seeds would duplicate evidence and are rejected. CLI ranges use an exclusive stop.
