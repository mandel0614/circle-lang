from __future__ import annotations

import numpy as np

from .compiler_m77 import (
    BUDGET,
    MAX_NAV_GAIN,
    DEADLINE_STEP,
    HAZARD_RELEASE_GUARD,
    TARGET_CELLS_REQUIRED,
    FORBIDDEN_CELLS_ALLOWED,
    LinkerStepAudit,
    causal_homeostasis_request,
    _allocate_strict,
    _allocate_deadline_relaxed,
)
from .compiler_m79 import TARGET_DEFICIT_SCALE, EMERGENCY_RISK_RESERVE

FORBIDDEN_THRESHOLD = 0.70


def _topk_mask(score, candidate, k_per_run):
    score=np.asarray(score,float); candidate=np.asarray(candidate,bool)
    out=np.zeros_like(candidate,bool)
    for i in range(candidate.shape[0]):
        idx=np.flatnonzero(candidate[i]); k=int(k_per_run[i])
        if k<=0 or len(idx)==0:
            continue
        if len(idx)<=k:
            out[i,idx]=True
        else:
            order=idx[np.lexsort((idx,-score[i,idx]))]
            out[i,order[:k]]=True
    return out


def allocate_viability_debt_step_v3(
    *,
    t,
    A,
    B,
    H,
    toward_gain,
    away_gain,
    goal_satisfied,
    forbidden_ever,
    intentional_risk_debt,
    relaxed_B_upper_bound,
    strict_B_upper_bound,
):
    """M7.10 causal viability/debt linker v3.

    v3 keeps the v2 target-deficit contract margin for genuinely risky relaxed
    actions, but separates relaxed actions into two classes using the current
    runtime model:

    1. robust-safe relaxed action:
       one-step worst-case B upper bound remains below the declared forbidden
       boundary 0.70. It can be executed without consuming intentional risk
       debt and is not blocked by the empirical base guard 0.53.

    2. risky relaxed action:
       worst-case B may cross 0.70. It remains subject to the v2 dynamic release
       guard and can be admitted only by the population risk-debt ledger.

    The risk-debt ledger is causal and persistent within a run. Once a cell is
    admitted as intentionally risky, its debt token is not recycled. Current
    strict-risk cells and the already-frozen one-cell emergency stochastic
    reserve are debited before new risky cells are admitted.

    No future realized noise, future disturbance, world ID, seed, or future
    trajectory is used.
    """
    A=np.asarray(A,float); B=np.asarray(B,float); H=np.asarray(H,float)
    toward_gain=np.asarray(toward_gain,float); away_gain=np.asarray(away_gain,float)
    goal_satisfied=np.asarray(goal_satisfied,bool)
    forbidden_ever=np.asarray(forbidden_ever,bool)
    debt=np.asarray(intentional_risk_debt,bool).copy()
    relaxed_B_upper_bound=np.asarray(relaxed_B_upper_bound,float)
    strict_B_upper_bound=np.asarray(strict_B_upper_bound,float)

    d_goal=np.clip(toward_gain/MAX_NAV_GAIN,0,1)
    d_safety=np.clip(away_gain/MAX_NAV_GAIN,0,1)
    homeo_command,d_invariant,invariant_reserve=causal_homeostasis_request(H)
    g0,s0,h0=_allocate_strict(d_goal,d_safety,d_invariant,invariant_reserve)
    g1,s1,h1=_allocate_deadline_relaxed(d_goal,d_safety,d_invariant,invariant_reserve)

    target_count=np.sum(goal_satisfied,axis=1)
    missing=np.maximum(TARGET_CELLS_REQUIRED-target_count,0)
    time_pressure=np.clip((t-DEADLINE_STEP)/max((200-1-DEADLINE_STEP),1),0.0,1.0)
    completion_pressure=np.clip(missing/TARGET_DEFICIT_SCALE,0.0,1.0)
    release_fraction=time_pressure*completion_pressure
    release_guard=HAZARD_RELEASE_GUARD+(FORBIDDEN_THRESHOLD-HAZARD_RELEASE_GUARD)*release_fraction

    base=(
        (t>=DEADLINE_STEP)
        & (~goal_satisfied)
        & (d_safety>1e-15)
        & (target_count<TARGET_CELLS_REQUIRED)[:,None]
    )

    # Key v3 change: runtime-certified robust-safe goal actions are not blocked
    # by the development-fitted 0.53 base guard.
    robust_safe=base & (relaxed_B_upper_bound<FORBIDDEN_THRESHOLD)
    already_forbidden=base & forbidden_ever

    risky_new=(
        base
        & (~robust_safe)
        & (~forbidden_ever)
        & (~debt)
        & (B<=release_guard[:,None])
    )

    strict_risk=(
        (~forbidden_ever)
        & (~debt)
        & (strict_B_upper_bound>=FORBIDDEN_THRESHOLD)
    )
    strict_risk_count=np.sum(strict_risk,axis=1)

    # Conservative stochastic debt accounting. Actual forbidden cells,
    # persistent intentional risk commitments, currently strict-risk cells and
    # one frozen emergency reserve all reduce admission capacity.
    remaining=np.maximum(
        FORBIDDEN_CELLS_ALLOWED
        -np.sum(forbidden_ever,axis=1)
        -np.sum(debt,axis=1)
        -strict_risk_count
        -EMERGENCY_RISK_RESERVE,
        0,
    )
    admitted=_topk_mask(A,risky_new,remaining)
    debt |= admitted

    relaxed=robust_safe | already_forbidden | (base & debt)
    goal=np.where(relaxed,g1,g0)
    safety=np.where(relaxed,s1,s0)
    invariant=np.where(relaxed,h1,h0)

    total=goal+safety+invariant
    budget_violation=total>BUDGET+1e-12
    goal_scale=np.divide(goal,d_goal,out=np.zeros_like(goal),where=d_goal>1e-15)
    safety_scale=np.divide(safety,d_safety,out=np.zeros_like(safety),where=d_safety>1e-15)
    inv_scale=np.divide(invariant,d_invariant,out=np.zeros_like(invariant),where=d_invariant>1e-15)

    audit=LinkerStepAudit(
        goal_allocation=goal,
        safety_allocation=safety,
        invariant_allocation=invariant,
        relaxed_mask=relaxed,
        contention=(d_goal+d_safety+d_invariant)>BUDGET+1e-12,
        budget_violation=budget_violation,
    )
    return (
        toward_gain*goal_scale,
        away_gain*safety_scale,
        homeo_command*inv_scale,
        audit,
        debt,
        {
            'release_guard':release_guard,
            'robust_safe_count':np.sum(robust_safe,axis=1),
            'strict_risk_count':strict_risk_count,
            'new_risk_debt_count':np.sum(admitted,axis=1),
            'risk_debt_count':np.sum(debt,axis=1),
        },
    )
