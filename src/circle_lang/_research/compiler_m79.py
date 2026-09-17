from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .compiler_m77 import (
    BUDGET,
    MAX_NAV_GAIN,
    MAX_HOMEOSTASIS_CONTROL,
    DEADLINE_STEP,
    HAZARD_RELEASE_GUARD,
    HOMEOSTASIS_TRIGGER_HALFWIDTH,
    TARGET_CELLS_REQUIRED,
    FORBIDDEN_CELLS_ALLOWED,
    LinkerStepAudit,
    causal_homeostasis_request,
    _allocate_strict,
    _allocate_deadline_relaxed,
)

# M7.9 v2 development-fitted constants.
TARGET_DEFICIT_SCALE = TARGET_CELLS_REQUIRED / 2.0  # 26 cells
EMERGENCY_RISK_RESERVE = 1


def _topk_mask(score, candidate, k_per_run):
    score=np.asarray(score,float); candidate=np.asarray(candidate,bool)
    out=np.zeros_like(candidate,bool)
    for i in range(candidate.shape[0]):
        idx=np.flatnonzero(candidate[i]); k=int(k_per_run[i])
        if k<=0 or len(idx)==0: continue
        if len(idx)<=k:
            out[i,idx]=True
        else:
            # Stable causal ranking: highest current target field A, then index.
            order=idx[np.lexsort((idx,-score[i,idx]))]
            out[i,order[:k]]=True
    return out


def allocate_contract_margin_step_v2(
    *, t, A, B, H, toward_gain, away_gain, goal_satisfied, forbidden_ever,
    relaxed_B_upper_bound, strict_B_upper_bound,
):
    """M7.9 causal risk-reserved contract-margin linker.

    Runtime adapter inputs `*_B_upper_bound` are one-step worst-case hazard
    bounds computed from the declared abstract Gaussian hazard model and the
    known movement-noise magnitude. They do not use the realized future noise
    direction.

    The linker keeps the M7.7 deadline but replaces the fixed release guard with
    a target-deficit-dependent margin. Intentional hazard-risk actions are
    allocated atomically after reserving capacity for currently strict-risk
    cells plus one development-fitted emergency slot.
    """
    A=np.asarray(A,float);B=np.asarray(B,float);H=np.asarray(H,float)
    toward_gain=np.asarray(toward_gain,float);away_gain=np.asarray(away_gain,float)
    goal_satisfied=np.asarray(goal_satisfied,bool);forbidden_ever=np.asarray(forbidden_ever,bool)
    relaxed_B_upper_bound=np.asarray(relaxed_B_upper_bound,float)
    strict_B_upper_bound=np.asarray(strict_B_upper_bound,float)

    d_goal=np.clip(toward_gain/MAX_NAV_GAIN,0,1)
    d_safety=np.clip(away_gain/MAX_NAV_GAIN,0,1)
    homeo_command,d_invariant,invariant_reserve=causal_homeostasis_request(H)
    g0,s0,h0=_allocate_strict(d_goal,d_safety,d_invariant,invariant_reserve)
    g1,s1,h1=_allocate_deadline_relaxed(d_goal,d_safety,d_invariant,invariant_reserve)

    target_count=np.sum(goal_satisfied,axis=1)
    missing=np.maximum(TARGET_CELLS_REQUIRED-target_count,0)
    time_pressure=np.clip(
        (t-DEADLINE_STEP)/max((200-1-DEADLINE_STEP),1),0.0,1.0
    )
    completion_pressure=np.clip(missing/TARGET_DEFICIT_SCALE,0.0,1.0)
    release_fraction=time_pressure*completion_pressure
    release_guard=(
        HAZARD_RELEASE_GUARD
        +(0.70-HAZARD_RELEASE_GUARD)*release_fraction
    )

    candidate=(
        (t>=DEADLINE_STEP)
        & (~goal_satisfied)
        & (d_safety>1e-15)
        & (target_count<TARGET_CELLS_REQUIRED)[:,None]
        & (B<=release_guard[:,None])
    )

    robust_safe=(candidate & (relaxed_B_upper_bound<0.70))
    already_forbidden=candidate & forbidden_ever
    risky_new=candidate & (~forbidden_ever) & (~robust_safe)

    strict_risk=(~forbidden_ever) & (strict_B_upper_bound>=0.70)
    strict_risk_count=np.sum(strict_risk,axis=1)
    emergency=(strict_risk_count>0).astype(int)*EMERGENCY_RISK_RESERVE
    remaining=np.maximum(
        FORBIDDEN_CELLS_ALLOWED
        -np.sum(forbidden_ever,axis=1)
        -strict_risk_count
        -emergency,
        0,
    )
    reserved_risky=_topk_mask(A,risky_new,remaining)

    relaxed=robust_safe|already_forbidden|reserved_risky
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
        {
            'release_guard':release_guard,
            'strict_risk_count':strict_risk_count,
            'risky_reserved_count':np.sum(reserved_risky,axis=1),
        },
    )
