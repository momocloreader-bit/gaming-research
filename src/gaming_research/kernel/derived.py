from __future__ import annotations

from gaming_research.kernel.types import Derived, Params


def F1(v: float, min1: float, max1: float) -> float:
    return (v - min1) / (max1 - min1)


def F2(v: float, min2: float, max2: float) -> float:
    return (v - min2) / (max2 - min2)


def compute_derived(params: Params) -> Derived:
    min1 = float(params.min1)
    max1 = float(params.max1)
    min2 = float(params.min2)
    max2 = float(params.max2)
    a1 = float(params.a1)
    a2 = float(params.a2)
    c1 = float(params.c1)
    c2 = float(params.c2)
    p = float(params.p)

    v1_star = (c1 - a1) / p
    v2_star = (c2 - a2) / (1.0 - p)

    span1 = max1 - min1
    span2 = max2 - min2

    f1 = (v1_star - min1) / span1 if span1 != 0.0 else float("nan")
    f2 = (v2_star - min2) / span2 if span2 != 0.0 else float("nan")

    one_minus_f1 = 1.0 - f1
    one_minus_f2 = 1.0 - f2

    # GT_rhs is undefined when F2(v2_star) == 0; leave as inf/nan so validation catches it
    gt_rhs = (one_minus_f2 * a1) / f2 if f2 != 0.0 else float("inf")
    gt_condition = v1_star <= gt_rhs

    return Derived(
        v1_star=v1_star,
        v2_star=v2_star,
        F1_v1_star=f1,
        F2_v2_star=f2,
        one_minus_F1_v1_star=one_minus_f1,
        one_minus_F2_v2_star=one_minus_f2,
        GT_rhs=gt_rhs,
        GT_condition=gt_condition,
    )
