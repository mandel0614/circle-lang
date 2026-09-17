# Execution semantics and scientific limits

All quantities are abstract simulation coordinates or dimensionless state/control variables. No mapping to physical minutes, micrometres, molecular concentrations, or biological actuators is asserted. Unless specified otherwise, comparisons include their stated boundaries.

## Logical state

All inputs default LOW, states default INACTIVE, and baseline phenotype values are motility = 1, division = 1, secretion = 0. Each state round evaluates conditions against a common snapshot. State actions apply synchronously; absent actions retain the previous value. Opposing actions on one state cause an error. Convergence must occur within 32 rounds. After convergence, matching phenotype actions execute once in source order. Increase/decrease multiply motility or division by 2/0.5; secretion is set to 1/0. This follows the M0.5 update model, with no spatial or biochemical interpretation.

## Navigation: M8.6 abstract backend

64 cells start independently at x ~ U(0.05,0.18), y ~ U(0.43,0.57). Each Gaussian field has value exp(−||p−c||²/(2σ²)). Its direction is the normalized analytical gradient, set to zero when its gradient norm is at most 10⁻¹².

Let A and B be field values clipped to [0,1]:

```text
s = 0.34 + 0.66 A^2.5
threshold = 0.018 + 0.42 A^2.5
toward = 3 clip(1 − (B/s)^2, 0, 1)
away = 3 clip((B − threshold)/0.18, 0, 1)^1.15
p_next = clip(p + 0.01(toward × dir_A − away × dir_B) + R ξ, 0, 1)
```

ξ is a normalized Gaussian random direction. R is the world's random displacement magnitude. There is no external B ≥ 0.20 sensing gate in this M8.6 adapter. Movement runs for 190 ticks.

Target occupancy is the endpoint fraction within radius 0.16 of the target. Forbidden entry is the fraction of cells ever observed at B ≥ 0.70 on **pre-update** states 0–189; final state 190 is not additionally sampled. Historical task criteria are occupancy ≥ 0.80 and forbidden entry ≤ 0.10. Mean final distance is measured in normalized domain units.

## Homeostasis: M6.3

64 independent states initialize uniformly on [0.44,0.56]. Sensor output is clipped to [0,1] after gain/offset transformation. Recompiled lowering subtracts the offset, divides by gain, and clips again. Clipping can lose information; inverse calibration cannot recover clipped values.

```text
risk = max(1, max(disturbance_multiplier, noise_multiplier) / actuator_efficiency)
center = (low + high)/2
trigger_halfwidth = (high − low)/(2 risk)
u = +0.035 below lower trigger; −0.035 above upper trigger; 0 otherwise
H_next = clip(H + 0.002(0.5−H) + actuator_efficiency × u
              + disturbance_multiplier × disturbance[t]
              + Normal(0, 0.0035 × noise_multiplier), 0, 1)
```

There are 200 updates. The six supplied disturbances preserve the archived pulse, bias, and stochastic-burst generators and RNG consumption. Band occupancy uses post-update history indices 10–199 (190 samples), measured against the source interval. Unsafe-state fraction uses all 200 samples and H ≤ 0.15 or H ≥ 0.85. Recovery checks whether at least 90% of cells are in band at any post-update history index from an episode's end index through end+20 inclusive, capped at 199; recovery fraction averages over eligible episode ends. No eligible episodes yields 1. Historical per-run criteria are occupancy ≥ 0.80, unsafe ≤ 0.05, recovery ≥ 0.80. `mean_abs_error` retains the archived reference |H−0.5| even if the requested interval changes.

## Composition: M7.18 frozen v3

64 cells run for 200 ticks in [0,100]²; target radius is 16. R1 supplies raw navigation requests, with the archived B ≥ 0.20 avoidance gate. Direction vectors point geometrically toward field centers. Initial positions, state initializations, motion noise, state noise, and disturbance streams preserve the M7.18 generator and seed offsets.

The per-cell shared budget is 0.75. Navigation demand is raw gain/3; homeostasis demand is |u|/0.035. State requests activate outside [0.425,0.575], with a state-dependent reservation. The strict ordering allocates safety, reserved state control, target motion, then remaining state control. The relaxed ordering allocates reserved state control, target motion, safety, then remaining state control.

The v3 linker uses current target occupancy, one-step hazard bounds, a deadline starting at tick 70, persistent intentional risk debt, and deterministic ranking by target field then cell index. Fixed quota constants are 52 target cells and 6 forbidden cells, with one emergency reserve. The release executes the exact archived allocation functions; see `_research/compiler_m710.py` and its dependencies for the full algorithm. Threshold changes in `require` affect evaluation only; they do not alter these internal quotas.

Spatial exposure is sampled before each update. State occupancy excludes post-update indices 0–9; unsafe fraction uses all 200 indices. Recovery is a single check at the configured disturbance end through end+20 inclusive. Historical joint criteria combine navigation and state thresholds above with zero budget violations. The frozen source interval and budget are mandatory. Source acceptance and successful execution do not perform the archived capacity probe, prospective admission, calibration/holdout split, or uncertainty analysis. No historical certificate is inherited.

## Cohesion: frozen M9.6 policy in M9.12 abstract runtime

64 cells move for 220 ticks in [0,1]². Pairwise displacement vectors with distance at most 10⁻¹² are excluded from controller sensing. Communication uses cutoff 0.38 and Gaussian width 0.14. Each cell averages neighbor unit directions with Gaussian weights. Short-range repulsion acts below 0.05; local density counts other cells below 0.10 and divides by 63.

Connected components under a strict 0.05 spacing threshold share their mean cohesion vector. This component computation is centralized in the reference runtime and does not establish a distributed implementation.

```text
ell = 0.03 + 0.02 (density + noise)
r = ell / (nearest_distance + ell)
self_weight = 0.2 (1−r)
group_weight = 0.8 (1−r)
repulsion_weight = r
step = 0.012 (self_weight × cohesion
              + group_weight × component_mean
              + repulsion_weight × unit_repulsion)
```

Deterministic step magnitude is capped at 0.016. Noise is added afterward, then positions are clipped to [0,1]. The no-interaction control retains only the defined repulsion safety rule.

Metrics are endpoint values: giant-component fraction uses graph edges of distance ≤ 0.15; radius of gyration is RMS distance from the population centroid; overcrowding is the fraction with a nearest neighbor at distance < 0.025. Unlike controller sensing, the overcrowding metric counts coincident cells. Historical task criteria are component fraction ≥ 0.85, radius ≤ 0.18, overcrowding ≤ 0.10.

## Meaning of an outcome

A compiled program has valid syntax, supported semantics, and a selected kernel. A completed run produced finite output. A contract pass satisfies the user's specified empirical comparisons on the listed seeds. These are separate statements. None constitutes prospective certification, statistical generalization, wet-lab validity, or equivalence to the external PhysiCell backend. Software regression cases are deliberately reused observed data.
