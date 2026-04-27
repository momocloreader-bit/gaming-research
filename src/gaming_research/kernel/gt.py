from __future__ import annotations

from gaming_research.kernel.derived import F1, F2
from gaming_research.kernel.types import Derived, Options, Params, Solution


def solve_gt(params: Params, derived: Derived, options: Options) -> tuple[tuple[Solution, ...], str]:
    min1 = float(params.min1)
    max1 = float(params.max1)
    min2 = float(params.min2)
    max2 = float(params.max2)
    c1 = float(params.c1)
    p = float(params.p)

    f2 = derived.F2_v2_star
    v2_star = derived.v2_star

    denominator = p + (1.0 - p) * f2
    if abs(denominator) < options.denom_eps:
        return (), "gt_invalid_denominator"

    v1_hat = ((1.0 - f2) * c1) / denominator
    v2_hat = v2_star

    in_support = (min1 <= v1_hat <= max1) and (min2 <= v2_hat <= max2)

    f1_hat = F1(v1_hat, min1, max1)
    f2_hat = F2(v2_hat, min2, max2)

    solution = Solution(
        source="GT",
        root_kind="closed_form",
        root_index=0,
        v1_hat=v1_hat,
        v2_hat=v2_hat,
        in_support=in_support,
        F1_v1_hat=f1_hat,
        F2_v2_hat=f2_hat,
        m_star=None,
    )

    if in_support:
        status_detail = "gt_valid_solution"
    else:
        status_detail = "gt_candidate_out_of_support"

    return (solution,), status_detail
