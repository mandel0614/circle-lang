from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from .bioir_m6 import HomeostasisBioIR


@dataclass(frozen=True)
class HomeostasisRuntimeContext:
    context_id: str
    state_sensor_gain: float
    state_sensor_offset: float
    actuator_efficiency: float
    disturbance_multiplier: float
    noise_multiplier: float

    def validate(self):
        if self.state_sensor_gain <= 0:
            raise ValueError('state_sensor_gain must be > 0')
        if self.actuator_efficiency <= 0:
            raise ValueError('actuator_efficiency must be > 0')
        if self.disturbance_multiplier <= 0:
            raise ValueError('disturbance_multiplier must be > 0')
        if self.noise_multiplier <= 0:
            raise ValueError('noise_multiplier must be > 0')


@dataclass(frozen=True)
class CompiledHomeostasisProgram:
    cell_name: str
    state_name: str
    low: float
    high: float
    controller: Callable
    runtime: HomeostasisRuntimeContext
    max_control: float
    lowering_mode: str
    trigger_low_canonical: float
    trigger_high_canonical: float


def compile_for_runtime(
    ir: HomeostasisBioIR,
    context: HomeostasisRuntimeContext,
    *,
    max_control: float = 0.035,
    mode: str,
) -> CompiledHomeostasisProgram:
    """Lower one canonical homeostasis behavior to a runtime context.

    naive:
        The canonical interval [low, high] is applied directly to the observed
        sensor value. Runtime sensor calibration and capability changes are not
        compensated.

    recompiled_v1:
        1. De-calibrate observed state into canonical coordinates.
        2. Compute a runtime risk ratio:

              risk_scale = max(1,
                  max(disturbance_multiplier, noise_multiplier)
                  / actuator_efficiency)

        3. Narrow the *internal trigger deadband* around the same canonical
           setpoint by exactly risk_scale, so weaker/noisier runtimes start
           corrective action earlier:

              trigger_halfwidth = canonical_halfwidth / risk_scale

        The requested phenotype interval remains [low, high]; only the backend
        trigger envelope changes. No fitted coefficient is introduced.
    """
    context.validate()
    if mode not in {'naive', 'recompiled_v1'}:
        raise ValueError(f'Unsupported mode: {mode}')

    low = float(ir.behavior.low)
    high = float(ir.behavior.high)
    center = 0.5 * (low + high)
    half = 0.5 * (high - low)

    if mode == 'naive':
        trigger_low = low
        trigger_high = high

        def controller(observed_state):
            x = np.asarray(observed_state, dtype=float)
            u = np.zeros_like(x)
            u = np.where(x < trigger_low, +max_control, u)
            u = np.where(x > trigger_high, -max_control, u)
            return u

    else:
        risk_scale = max(
            1.0,
            max(
                context.disturbance_multiplier,
                context.noise_multiplier,
            ) / context.actuator_efficiency,
        )
        trigger_half = half / risk_scale
        trigger_low = center - trigger_half
        trigger_high = center + trigger_half

        def controller(observed_state):
            observed = np.asarray(observed_state, dtype=float)
            canonical = np.clip(
                (observed - context.state_sensor_offset)
                / context.state_sensor_gain,
                0.0,
                1.0,
            )
            u = np.zeros_like(canonical)
            u = np.where(canonical < trigger_low, +max_control, u)
            u = np.where(canonical > trigger_high, -max_control, u)
            return u

    return CompiledHomeostasisProgram(
        cell_name=ir.cell_name,
        state_name=ir.state.name,
        low=low,
        high=high,
        controller=controller,
        runtime=context,
        max_control=float(max_control),
        lowering_mode=mode,
        trigger_low_canonical=float(trigger_low),
        trigger_high_canonical=float(trigger_high),
    )
