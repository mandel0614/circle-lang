from __future__ import annotations

from dataclasses import dataclass

import numpy as np


BUDGET = 0.75
MAX_NAV_GAIN = 3.0
MAX_HOMEOSTASIS_CONTROL = 0.035

# Development-fitted on permanently observed M7.6 data only.
DEADLINE_STEP = 70
HAZARD_RELEASE_GUARD = 0.53

# Frozen from the M7.2/M7.3 homeostasis resource-contract semantics.
HOMEOSTASIS_TRIGGER_HALFWIDTH = 0.075

TARGET_CELLS_REQUIRED = 52
FORBIDDEN_CELLS_ALLOWED = 6


@dataclass(frozen=True)
class LinkerStepAudit:
    goal_allocation: np.ndarray
    safety_allocation: np.ndarray
    invariant_allocation: np.ndarray
    relaxed_mask: np.ndarray
    contention: np.ndarray
    budget_violation: np.ndarray


def _allocate_strict(d_goal, d_safety, d_invariant, invariant_reserve):
    rem = np.full_like(d_goal, BUDGET)

    safety = np.minimum(d_safety, rem)
    rem -= safety

    inv_res = np.minimum(invariant_reserve, rem)
    rem -= inv_res

    goal = np.minimum(d_goal, rem)
    rem -= goal

    inv_extra = np.minimum(np.maximum(d_invariant - inv_res, 0.0), rem)
    invariant = inv_res + inv_extra

    return goal, safety, invariant


def _allocate_deadline_relaxed(d_goal, d_safety, d_invariant, invariant_reserve):
    """Causal deadline-aware exception ordering.

    Preserve the state-derived invariant reservation, then prioritize goal
    completion over hazard avoidance. Any remaining budget is returned to
    safety and then extra invariant control.

    This does not alter BUDGET or any phenotype threshold.
    """
    rem = np.full_like(d_goal, BUDGET)

    inv_res = np.minimum(invariant_reserve, rem)
    rem -= inv_res

    goal = np.minimum(d_goal, rem)
    rem -= goal

    safety = np.minimum(d_safety, rem)
    rem -= safety

    inv_extra = np.minimum(np.maximum(d_invariant - inv_res, 0.0), rem)
    invariant = inv_res + inv_extra

    return goal, safety, invariant


def causal_homeostasis_request(H):
    """Return signed canonical homeostasis command and normalized demands.

    The preventive trigger is centered at 0.5 with halfwidth 0.075.
    Resource reservation grows only as the state approaches the phenotype
    boundary at |H-0.5| = 0.10.
    """
    H = np.asarray(H, dtype=float)
    dev = np.abs(H - 0.5)

    command = np.where(
        H < 0.5 - HOMEOSTASIS_TRIGGER_HALFWIDTH,
        +MAX_HOMEOSTASIS_CONTROL,
        np.where(
            H > 0.5 + HOMEOSTASIS_TRIGGER_HALFWIDTH,
            -MAX_HOMEOSTASIS_CONTROL,
            0.0,
        ),
    )

    demand = np.abs(command) / MAX_HOMEOSTASIS_CONTROL

    urgency = np.clip(
        (dev - HOMEOSTASIS_TRIGGER_HALFWIDTH)
        / (0.10 - HOMEOSTASIS_TRIGGER_HALFWIDTH),
        0.0,
        1.0,
    )
    reserve = np.minimum(demand * urgency, BUDGET)
    return command, demand, reserve


def allocate_causal_step(
    *,
    mode: str,
    t: int,
    A,
    B,
    H,
    toward_gain,
    away_gain,
    goal_satisfied,
    forbidden_ever,
):
    """Allocate one causal composition step.

    Observable inputs only:
      - current A, B, H
      - component command requests
      - current goal-satisfaction contract monitor
      - current forbidden-entry ledger
      - current time

    No future noise, future disturbance, world ID, seed, or future trajectory
    is used.

    Modes
    -----
    causal_strict_v5:
        safety -> invariant reserve -> goal -> extra invariant.

    deadline_contract_linker_v1:
        Same default execution. A sparse exception is permitted only when:
          1. t >= DEADLINE_STEP;
          2. the run has not yet satisfied the 52/64 target quota;
          3. this cell is not currently goal-satisfied;
          4. B <= HAZARD_RELEASE_GUARD;
          5. the hazard component has nonzero demand;
          6. the forbidden ledger has fewer than six cells, or this cell has
             already consumed forbidden slack.

        The exception ordering is:
          invariant reserve -> goal -> safety -> extra invariant.
    """
    if mode not in {"causal_strict_v5", "deadline_contract_linker_v1"}:
        raise ValueError(f"Unsupported M7.7 linker mode: {mode}")

    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    H = np.asarray(H, dtype=float)
    toward_gain = np.asarray(toward_gain, dtype=float)
    away_gain = np.asarray(away_gain, dtype=float)
    goal_satisfied = np.asarray(goal_satisfied, dtype=bool)
    forbidden_ever = np.asarray(forbidden_ever, dtype=bool)

    d_goal = np.clip(toward_gain / MAX_NAV_GAIN, 0.0, 1.0)
    d_safety = np.clip(away_gain / MAX_NAV_GAIN, 0.0, 1.0)

    homeo_command, d_invariant, invariant_reserve = causal_homeostasis_request(H)

    g0, s0, h0 = _allocate_strict(
        d_goal, d_safety, d_invariant, invariant_reserve
    )

    if mode == "causal_strict_v5":
        relaxed = np.zeros_like(goal_satisfied, dtype=bool)
        goal, safety, invariant = g0, s0, h0
    else:
        target_count = np.sum(goal_satisfied, axis=1)
        target_quota_unmet = target_count < TARGET_CELLS_REQUIRED

        forbidden_count = np.sum(forbidden_ever, axis=1)
        forbidden_quota_open = forbidden_count < FORBIDDEN_CELLS_ALLOWED

        relaxed = (
            (t >= DEADLINE_STEP)
            & (~goal_satisfied)
            & (B <= HAZARD_RELEASE_GUARD)
            & (d_safety > 1e-15)
            & target_quota_unmet[:, None]
            & (forbidden_quota_open[:, None] | forbidden_ever)
        )

        g1, s1, h1 = _allocate_deadline_relaxed(
            d_goal, d_safety, d_invariant, invariant_reserve
        )

        goal = np.where(relaxed, g1, g0)
        safety = np.where(relaxed, s1, s0)
        invariant = np.where(relaxed, h1, h0)

    total = goal + safety + invariant
    budget_violation = total > BUDGET + 1e-12

    goal_scale = np.divide(
        goal, d_goal,
        out=np.zeros_like(goal),
        where=d_goal > 1e-15,
    )
    safety_scale = np.divide(
        safety, d_safety,
        out=np.zeros_like(safety),
        where=d_safety > 1e-15,
    )
    invariant_scale = np.divide(
        invariant, d_invariant,
        out=np.zeros_like(invariant),
        where=d_invariant > 1e-15,
    )

    return (
        toward_gain * goal_scale,
        away_gain * safety_scale,
        homeo_command * invariant_scale,
        LinkerStepAudit(
            goal_allocation=goal,
            safety_allocation=safety,
            invariant_allocation=invariant,
            relaxed_mask=relaxed,
            contention=(d_goal + d_safety + d_invariant) > BUDGET + 1e-12,
            budget_violation=budget_violation,
        ),
    )
