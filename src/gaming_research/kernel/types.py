from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Params:
    min1: float | Decimal
    max1: float | Decimal
    min2: float | Decimal
    max2: float | Decimal
    a1: float | Decimal
    a2: float | Decimal
    c1: float | Decimal
    c2: float | Decimal
    p: float | Decimal


@dataclass(frozen=True)
class Options:
    enforce_war_payoff_s1: bool = True
    enforce_war_payoff_s2: bool = True
    bluffing_solver_mode: Literal["compat", "research"] = "research"
    bluffing_sample_count: int = 200
    xtol: float = 1e-12
    rtol: float = 8.881784197001252e-16
    zero_tol: float = 1e-9
    dedup_tol: float = 1e-6
    denom_eps: float = 1e-12


@dataclass(frozen=True)
class Derived:
    v1_star: float
    v2_star: float
    F1_v1_star: float
    F2_v2_star: float
    one_minus_F1_v1_star: float
    one_minus_F2_v2_star: float
    GT_rhs: float
    GT_condition: bool


@dataclass(frozen=True)
class Validation:
    passed: bool
    failure_codes: tuple[str, ...]
    failure_messages: tuple[str, ...]


@dataclass(frozen=True)
class Branch:
    scenario: Literal["GT", "bluffing"]
    solver_mode: Literal["closed_form", "compat", "research"]


@dataclass(frozen=True)
class Solution:
    source: Literal["GT", "bluffing"]
    root_kind: Literal["closed_form", "numerical"]
    root_index: int
    v1_hat: float
    v2_hat: float
    in_support: bool
    F1_v1_hat: float
    F2_v2_hat: float
    m_star: float | None


@dataclass(frozen=True)
class Summary:
    status: Literal["validation_failed", "solver_has_valid_solution", "solver_no_valid_solution"]
    status_detail: str
    valid_solution_count: int
    selected_solution_index: int | None


@dataclass(frozen=True)
class KernelResult:
    params: Params
    derived: Derived | None
    validation: Validation
    branch: Branch | None
    solutions: tuple[Solution, ...]
    summary: Summary
