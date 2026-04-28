from decimal import Decimal

import pytest

from gaming_research.kernel import Options, Params, evaluate_case


# Baseline valid params (bluffing branch): min1=1, max1=10, min2=1, max2=10,
# a1=2, a2=2, c1=5, c2=5, p=0.4
# v1_star = (5-2)/0.4 = 7.5  in (1,10)
# v2_star = (5-2)/0.6 = 5.0  in (1,10)
# p*max1-c1 = 0.4*10-5 = -1 < 0  OK
# (1-p)*max2-c2 = 0.6*10-5 = 1 > 0  fails war payoff s2 -- need different params

# Use p=0.8: v1_star=(5-2)/0.8=3.75, v2_star=(5-2)/0.2=15 -- out of (1,10)
# Try: min1=1,max1=10,min2=1,max2=20, a1=2,a2=2,c1=5,c2=5, p=0.8
# v1_star=3.75 in (1,10) OK; v2_star=15 in (1,20) OK
# p*max1-c1=0.8*10-5=3 > 0 -- fails s1
# Try p=0.9: v1_star=3/0.9=3.33, v2_star=3/0.1=30, not in (1,20)
# Try: min1=1,max1=100,min2=1,max2=100, a1=2,a2=2,c1=10,c2=10, p=0.5
# v1_star=(10-2)/0.5=16 in (1,100); v2_star=16 in (1,100)
# p*max1-c1=0.5*100-10=40 > 0 fails
# Need p*max1 < c1  =>  p < c1/max1
# c1=10, max1=100: p < 0.1. Try p=0.05
# v1_star=(10-2)/0.05=160 not in (1,100)
# Try: min1=1,max1=1000,min2=1,max2=1000, a1=5,a2=5,c1=50,c2=50, p=0.04
# v1_star=(50-5)/0.04=1125 not in support
# Let's reason: v1_star = (c1-a1)/p < max1  =>  c1-a1 < p*max1
# and p*max1 < c1  =>  c1-a1 < c1  =>  a1 > 0 always true
# and v1_star > min1  =>  (c1-a1)/p > min1  =>  c1 > a1 + p*min1
# Combined: a1+p*min1 < c1 < p*max1 + a1... wait
# p*max1-c1 < 0  =>  c1 > p*max1
# v1_star = (c1-a1)/p > min1  =>  c1 > a1 + p*min1  (auto since c1>p*max1 > p*min1 > p*min1-a1... no)
# So: c1 > p*max1 AND v1_star=(c1-a1)/p < max1 => c1-a1 < p*max1 => c1 < p*max1+a1
# So: p*max1 < c1 < p*max1+a1, and c1>a1
# Try: p=0.5, max1=10, a1=3: p*max1=5, so 5 < c1 < 8. c1=6.
# v1_star=(6-3)/0.5=6, v2_star same if symmetric. Need v1_star in (min1,max1)=(1,10): 6 in (1,10) OK
# p*max1-c1=5-6=-1 <0 OK
# Similarly for s2: (1-p)*max2-c2 < 0 => c2 > (1-p)*max2
# p=0.5, max2=10, a2=3: (1-p)*max2=5, so c2 > 5 => c2=6
# v2_star=(6-3)/0.5=6 in (1,10) OK
VALID_PARAMS = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)


def test_passing_inputs():
    result = evaluate_case(VALID_PARAMS)
    v = result.validation
    assert v.passed is True
    assert v.failure_codes == ()
    assert v.failure_messages == ()


def test_all_positive():
    p = Params(min1=-1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)
    result = evaluate_case(p)
    assert "all_positive" in result.validation.failure_codes


def test_min1_lt_max1():
    p = Params(min1=10, max1=5, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)
    result = evaluate_case(p)
    assert "min1_lt_max1" in result.validation.failure_codes


def test_min2_lt_max2():
    p = Params(min1=1, max1=10, min2=10, max2=5, a1=3, a2=3, c1=6, c2=6, p=0.5)
    result = evaluate_case(p)
    assert "min2_lt_max2" in result.validation.failure_codes


def test_p_in_open_unit_interval_zero():
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.0)
    result = evaluate_case(p)
    assert "p_in_open_unit_interval" in result.validation.failure_codes


def test_p_in_open_unit_interval_one():
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=1.0)
    result = evaluate_case(p)
    assert "p_in_open_unit_interval" in result.validation.failure_codes


def test_c1_gt_a1():
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=7, a2=3, c1=6, c2=6, p=0.5)
    result = evaluate_case(p)
    assert "c1_gt_a1" in result.validation.failure_codes


def test_c2_gt_a2():
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=7, c1=6, c2=6, p=0.5)
    result = evaluate_case(p)
    assert "c2_gt_a2" in result.validation.failure_codes


def test_v1_star_in_support():
    # v1_star = (c1-a1)/p. With p=0.5, a1=1, c1=15: v1_star=28, outside (1,10)
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=1, a2=3, c1=15, c2=6, p=0.5)
    result = evaluate_case(p)
    assert "v1_star_in_support" in result.validation.failure_codes


def test_v2_star_in_support():
    # v2_star=(c2-a2)/(1-p). With p=0.5, a2=1, c2=15: v2_star=28, outside (1,10)
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=1, c1=6, c2=15, p=0.5)
    result = evaluate_case(p)
    assert "v2_star_in_support" in result.validation.failure_codes


def test_s1_war_payoff_negative():
    # p*max1-c1 >= 0: e.g., p=0.9, max1=10, c1=6 => 9-6=3 > 0
    # But need other checks to pass: c1>a1, v1_star in support
    # v1_star=(6-a1)/0.9 must be in (1,10). a1=2: v1_star=4.44 OK
    # v2_star=(c2-a2)/0.1 must be in (1,10). c2-a2 < 0.1*10=1. c2=2.5,a2=2: v2_star=5 OK
    # (1-p)*max2-c2=0.1*10-2.5=-1.5<0 OK
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=2, a2=2, c1=6, c2=2.5, p=0.9)
    result = evaluate_case(p)
    assert "s1_war_payoff_negative" in result.validation.failure_codes


def test_s2_war_payoff_negative():
    # (1-p)*max2-c2 >= 0: p=0.1, max2=10, c2=6 => 0.9*10-6=3 > 0
    # v1_star=(6-2)/0.1=40 not in (1,10)... let's try c1=2.5, a1=2
    # v1_star=(2.5-2)/0.1=5 in (1,10) OK; p*max1-c1=0.1*10-2.5=-1.5<0 OK
    # v2_star=(6-a2)/0.9 in (1,10). a2=2: v2_star=4.44 OK
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=2, a2=2, c1=2.5, c2=6, p=0.1)
    result = evaluate_case(p)
    assert "s2_war_payoff_negative" in result.validation.failure_codes


def test_war_payoff_s1_disabled():
    # Same as test_s1_war_payoff_negative but with enforce_war_payoff_s1=False
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=2, a2=2, c1=6, c2=2.5, p=0.9)
    opts = Options(enforce_war_payoff_s1=False)
    result = evaluate_case(p, opts)
    assert "s1_war_payoff_negative" not in result.validation.failure_codes


def test_war_payoff_s2_disabled():
    p = Params(min1=1, max1=10, min2=1, max2=10, a1=2, a2=2, c1=2.5, c2=6, p=0.1)
    opts = Options(enforce_war_payoff_s2=False)
    result = evaluate_case(p, opts)
    assert "s2_war_payoff_negative" not in result.validation.failure_codes


def test_validation_failed_status():
    p = Params(min1=10, max1=5, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)
    result = evaluate_case(p)
    assert result.summary.status == "validation_failed"
    assert result.branch is None
    assert result.solutions == ()


def test_decimal_params_accepted():
    p = Params(
        min1=Decimal("1"), max1=Decimal("10"),
        min2=Decimal("1"), max2=Decimal("10"),
        a1=Decimal("3"), a2=Decimal("3"),
        c1=Decimal("6"), c2=Decimal("6"),
        p=Decimal("0.5"),
    )
    result = evaluate_case(p)
    assert result.validation.passed is True
    # Original Decimal values echoed unchanged
    assert result.params.min1 == Decimal("1")
