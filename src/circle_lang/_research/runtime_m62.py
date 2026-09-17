from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .compiler_m62 import CompiledHomeostasisProgram

N_CELLS = 64
STEPS = 200
STATE_MIN = 0.0
STATE_MAX = 1.0
UNSAFE_LOW = 0.15
UNSAFE_HIGH = 0.85
RECOVERY_DEADLINE = 20
BASE_NATURAL_RELAXATION = 0.002
BASE_NOISE_SIGMA = 0.0035


@dataclass(frozen=True)
class DisturbanceScenario:
    name: str
    episodes: tuple[tuple[int, int, float], ...]
    bias_start: int | None = None
    bias_end: int | None = None
    bias_value: float = 0.0
    stochastic_bursts: bool = False


SCENARIOS = (
    DisturbanceScenario('positive_pulse', ((40, 70, +0.022),)),
    DisturbanceScenario('negative_pulse', ((50, 82, -0.022),)),
    DisturbanceScenario('alternating_pulses', (
        (35, 55, +0.020),
        (95, 115, -0.020),
        (150, 166, +0.017),
    )),
    DisturbanceScenario(
        'sustained_positive_bias', (),
        bias_start=30, bias_end=170, bias_value=+0.010,
    ),
    DisturbanceScenario('stochastic_bursts', (), stochastic_bursts=True),
    DisturbanceScenario(
        'mixed_disturbance',
        ((30, 50, -0.018), (84, 108, +0.021)),
        bias_start=122, bias_end=178, bias_value=+0.006,
    ),
)


def disturbance_trace(scenario, rng):
    d = np.zeros(STEPS, dtype=float)
    for start, end, amp in scenario.episodes:
        d[start:end] += amp
    if scenario.bias_start is not None:
        d[scenario.bias_start:scenario.bias_end] += scenario.bias_value
    if scenario.stochastic_bursts:
        occupied = np.zeros(STEPS, dtype=bool)
        for _ in range(4):
            for _attempt in range(100):
                start = int(rng.integers(25, 170))
                length = int(rng.integers(8, 18))
                end = min(start + length, STEPS)
                if not occupied[max(0,start-5):min(STEPS,end+5)].any():
                    break
            amp = float(rng.uniform(0.014, 0.023))
            sign = -1.0 if int(rng.integers(0,2)) == 0 else 1.0
            d[start:end] += sign * amp
            occupied[start:end] = True
    return d


def episode_ends(scenario, trace):
    ends = [end for _start, end, _amp in scenario.episodes]
    if scenario.bias_start is not None:
        ends.append(scenario.bias_end)
    if scenario.stochastic_bursts:
        active = np.abs(trace) > 1e-12
        for t in range(1, STEPS):
            if active[t-1] and not active[t]:
                ends.append(t)
        if active[-1]:
            ends.append(STEPS)
    return sorted(set(e for e in ends if e < STEPS))


def run_one(program: CompiledHomeostasisProgram, scenario, seed, observer=None):
    rng = np.random.default_rng(seed)
    c = program.runtime
    state = rng.uniform(0.44, 0.56, N_CELLS)
    trace = disturbance_trace(scenario, rng)
    history = np.zeros((STEPS, N_CELLS), dtype=float)

    if observer is not None: observer(0, state.copy())
    for t in range(STEPS):
        observed = np.clip(
            c.state_sensor_gain * state + c.state_sensor_offset,
            0.0, 1.0,
        )
        control = np.asarray(program.controller(observed), dtype=float)
        control = np.clip(control, -program.max_control, program.max_control)
        noise = rng.normal(
            0.0,
            BASE_NOISE_SIGMA * c.noise_multiplier,
            N_CELLS,
        )
        state = (
            state
            + BASE_NATURAL_RELAXATION * (0.5 - state)
            + c.actuator_efficiency * control
            + c.disturbance_multiplier * trace[t]
            + noise
        )
        state = np.clip(state, STATE_MIN, STATE_MAX)
        history[t] = state
        if observer is not None: observer(t+1, state.copy())

    in_band = (history >= program.low) & (history <= program.high)
    unsafe = (history <= UNSAFE_LOW) | (history >= UNSAFE_HIGH)
    band_occupancy = float(np.mean(in_band[10:]))
    unsafe_fraction = float(np.mean(unsafe))

    recovery_checks = []
    for end in episode_ends(scenario, trace):
        deadline = min(end + RECOVERY_DEADLINE, STEPS - 1)
        if deadline <= end:
            continue
        occupancies = np.mean(in_band[end:deadline+1], axis=1)
        recovery_checks.append(float(np.max(occupancies) >= 0.90))
    recovery_fraction = float(np.mean(recovery_checks)) if recovery_checks else 1.0

    passed = (
        band_occupancy >= 0.80
        and unsafe_fraction <= 0.05
        and recovery_fraction >= 0.80
    )
    return {
        'band_occupancy': band_occupancy,
        'unsafe_state_fraction': unsafe_fraction,
        'recovery_fraction': recovery_fraction,
        'mean_abs_error': float(np.mean(np.abs(history - 0.5))),
        'passed': float(passed),
    }
