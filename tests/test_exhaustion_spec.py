from __future__ import annotations

from decimal import Decimal

import pytest

from gaming_research.kernel.types import Options
from gaming_research.exhaustion.spec import (
    CURRENT_SPEC, GridSpec, estimate_case_count, reduction_eligible,
)

_default_options = Options()


def test_current_spec_valid_pair_count():
    pairs = [
        (min1, min2)
        for min1 in CURRENT_SPEC.min1_values
        for min2 in CURRENT_SPEC.min2_values
        if (min1 + CURRENT_SPEC.span1 / 2) - (min2 + CURRENT_SPEC.span2 / 2) >= CURRENT_SPEC.avg_diff_min
    ]
    assert len(pairs) == 35


def test_estimate_case_count_reduction():
    assert estimate_case_count(CURRENT_SPEC, _default_options) == 3920


def test_estimate_case_count_full_grid():
    opts = Options(enforce_war_payoff_s1=False)
    assert estimate_case_count(CURRENT_SPEC, opts) == 14_112_000


def test_reduction_eligible_default():
    assert reduction_eligible(CURRENT_SPEC, _default_options) is True


def test_reduction_eligible_war_payoff_off():
    opts = Options(enforce_war_payoff_s1=False)
    assert reduction_eligible(CURRENT_SPEC, opts) is False
