from __future__ import annotations

from dataclasses import dataclass



@dataclass(frozen=True)
class IRContinuousState:
    name: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class IRHomeostasis:
    state: str
    low: float
    high: float
    mode: str = "deadband_max_restore"


@dataclass(frozen=True)
class IRConstraint:
    metric: str
    op: str
    value: float


@dataclass(frozen=True)
class HomeostasisBioIR:
    cell_name: str
    state: IRContinuousState
    behavior: IRHomeostasis
    constraints: tuple[IRConstraint, ...]


