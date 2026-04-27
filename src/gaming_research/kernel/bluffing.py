from __future__ import annotations

import math
from typing import Callable

import scipy.optimize

from gaming_research.kernel.derived import F1, F2
from gaming_research.kernel.types import Derived, Options, Params, Solution


def build_residual(
    params: Params, derived: Derived, denom_eps: float
) -> Callable[[float], float]:
    min1 = float(params.min1)
    max1 = float(params.max1)
    min2 = float(params.min2)
    max2 = float(params.max2)
    a1 = float(params.a1)
    a2 = float(params.a2)
    c2 = float(params.c2)
    p = float(params.p)

    one_minus_f1 = derived.one_minus_F1_v1_star
    span1 = max1 - min1

    def residual(v1_hat: float) -> float:
        expr1 = min2 + (max2 - min2) * (a1 / (v1_hat + a1))

        numerator = span1 * one_minus_f1 * c2 - (max1 - v1_hat) * a2
        denominator = (max1 - v1_hat) - span1 * p * one_minus_f1

        if abs(denominator) < denom_eps:
            return float("nan")

        expr2 = numerator / denominator
        return expr1 - expr2

    return residual


def _make_solution(
    index: int,
    v1_hat: float,
    params: Params,
    derived: Derived,
) -> Solution:
    min1 = float(params.min1)
    max1 = float(params.max1)
    min2 = float(params.min2)
    max2 = float(params.max2)
    a1 = float(params.a1)

    v2_hat = min2 + (max2 - min2) * (a1 / (v1_hat + a1))
    in_support = (min1 <= v1_hat <= max1) and (min2 <= v2_hat <= max2)

    f1_hat = F1(v1_hat, min1, max1)
    f2_hat = F2(v2_hat, min2, max2)

    # m_star is a branch-level constant, computed once from derived quantities
    m_star = derived.F2_v2_star * derived.v1_star + (1.0 - derived.F2_v2_star) * (-float(params.a1))

    return Solution(
        source="bluffing",
        root_kind="numerical",
        root_index=index,
        v1_hat=v1_hat,
        v2_hat=v2_hat,
        in_support=in_support,
        F1_v1_hat=f1_hat,
        F2_v2_hat=f2_hat,
        m_star=m_star,
    )


def solve_compat(
    params: Params, derived: Derived, options: Options
) -> tuple[tuple[Solution, ...], str]:
    residual = build_residual(params, derived, options.denom_eps)
    min1 = float(params.min1)
    max1 = float(params.max1)
    v1_init = (min1 + max1) / 2.0

    result, _, flag, _ = scipy.optimize.fsolve(residual, v1_init, full_output=True)

    if flag != 1:
        return (), "bluffing_numerical_failure"

    v1_hat = float(result[0])

    # Check that fsolve didn't land on a discontinuity
    r = residual(v1_hat)
    if math.isnan(r) or abs(r) > options.zero_tol * 1e6:
        return (), "bluffing_numerical_failure"

    solution = _make_solution(0, v1_hat, params, derived)
    return (solution,), _single_solution_status(solution)


def solve_research(
    params: Params, derived: Derived, options: Options
) -> tuple[tuple[Solution, ...], str]:
    residual = build_residual(params, derived, options.denom_eps)
    min1 = float(params.min1)
    max1 = float(params.max1)
    n = options.bluffing_sample_count

    xs = [min1 + i * (max1 - min1) / (n - 1) for i in range(n)]
    ys = [residual(x) for x in xs]

    candidates: list[float] = []

    for i in range(len(xs)):
        yi = ys[i]
        if math.isnan(yi):
            continue
        # Direct near-zero hit
        if abs(yi) < options.zero_tol:
            candidates.append(xs[i])
            continue
        # Sign-change bracket with next sample
        if i + 1 < len(xs):
            yj = ys[i + 1]
            if math.isnan(yj):
                continue
            if yi * yj < 0.0:
                try:
                    root = scipy.optimize.brentq(
                        residual, xs[i], xs[i + 1],
                        xtol=options.xtol, rtol=options.rtol,
                    )
                    candidates.append(root)
                except ValueError:
                    pass

    # Deduplicate
    deduped: list[float] = []
    for c in sorted(candidates):
        if not deduped or abs(c - deduped[-1]) > options.dedup_tol:
            deduped.append(c)

    if not deduped:
        return (), "bluffing_no_root_found"

    solutions = tuple(_make_solution(i, v, params, derived) for i, v in enumerate(deduped))
    return solutions, _multi_solution_status(solutions)


def _single_solution_status(sol: Solution) -> str:
    return "bluffing_single_valid_root" if sol.in_support else "bluffing_root_found_but_out_of_support"


def _multi_solution_status(solutions: tuple[Solution, ...]) -> str:
    valid = [s for s in solutions if s.in_support]
    if not valid:
        return "bluffing_root_found_but_out_of_support"
    if len(valid) == 1:
        return "bluffing_single_valid_root"
    return "bluffing_multiple_valid_roots"
