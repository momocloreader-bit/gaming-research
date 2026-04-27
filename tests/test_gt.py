import pytest

from gaming_research.kernel import Options, Params, evaluate_case
from gaming_research.kernel.derived import compute_derived


# GT branch requires GT_condition: v1_star <= GT_rhs
# GT_rhs = (1-F2(v2_star)) * a1 / F2(v2_star)
# Use VALID_PARAMS from test_validation: min1=1,max1=10,min2=1,max2=10,a1=3,a2=3,c1=6,c2=6,p=0.5
# v1_star=6, v2_star=6
# F2(v2_star)=(6-1)/(10-1)=5/9
# GT_rhs=(4/9)*3/(5/9)=4*3/5=2.4
# GT_condition: v1_star=6 <= 2.4? NO => bluffing branch
# Need GT branch: v1_star <= GT_rhs
# GT_rhs = (1-f2)*a1/f2. Make f2 small (v2_star near min2).
# v2_star=(c2-a2)/(1-p). Keep p=0.5, make c2-a2 small.
# c2=a2+epsilon. But need c2>a2 and v2_star in (min2,max2).
# v2_star=(c2-a2)/0.5. If c2=3.5, a2=3: v2_star=1, not in (1,10) (open interval).
# c2=3.6, a2=3: v2_star=1.2 in (1,10). f2=(1.2-1)/9=0.0222
# GT_rhs=(1-0.0222)*3/0.0222 ≈ 132. v1_star=(c1-a1)/0.5.
# Need v1_star <= 132 and in (1,10): easy. c1=6,a1=3: v1_star=6 <= 132 => GT
# Check war payoffs: p*max1-c1=5-6=-1<0 OK; (1-p)*max2-c2=5-3.6=1.4 > 0 FAIL
# Need (1-p)*max2 < c2: 0.5*10=5 < c2. c2=5.5, a2=3: v2_star=(5.5-3)/0.5=5 in (1,10)
# f2=(5-1)/9=4/9; GT_rhs=(5/9)*3/(4/9)=15/4=3.75; v1_star=6 <= 3.75? NO
# c2=5.5, a2=4: v2_star=(5.5-4)/0.5=3 in (1,10); f2=(3-1)/9=2/9
# GT_rhs=(7/9)*3/(2/9)=21/2=10.5; v1_star=6<=10.5 YES => GT!
# p*max1-c1=5-6=-1<0 OK; (1-p)*max2-c2=5-5.5=-0.5<0 OK
GT_PARAMS = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=4, c1=6, c2=5.5, p=0.5)


def test_gt_branch_selected():
    result = evaluate_case(GT_PARAMS)
    assert result.validation.passed is True
    assert result.branch.scenario == "GT"
    assert result.branch.solver_mode == "closed_form"


def test_gt_closed_form_values():
    result = evaluate_case(GT_PARAMS)
    derived = result.derived
    # v1_hat = (1-F2(v2_star))*c1 / (p + (1-p)*F2(v2_star))
    f2 = derived.F2_v2_star
    expected_v1_hat = ((1 - f2) * 6.0) / (0.5 + 0.5 * f2)
    sol = result.solutions[0]
    assert sol.v1_hat == pytest.approx(expected_v1_hat, rel=1e-9)
    assert sol.v2_hat == pytest.approx(derived.v2_star, rel=1e-9)
    assert sol.source == "GT"
    assert sol.root_kind == "closed_form"
    assert sol.root_index == 0
    assert sol.m_star is None


def test_gt_valid_solution_status():
    result = evaluate_case(GT_PARAMS)
    assert result.summary.status == "solver_has_valid_solution"
    assert result.summary.status_detail == "gt_valid_solution"
    assert result.summary.valid_solution_count == 1
    assert result.summary.selected_solution_index == 0


def test_gt_out_of_support():
    # Make v1_hat fall outside [min1, max1].
    # v1_hat = (1-f2)*c1 / (p+(1-p)*f2). Make c1 very small so v1_hat < min1.
    # But c1>a1 and v1_star=(c1-a1)/p must be in support.
    # Easier: shift min1 so that the computed v1_hat is outside.
    # Use GT_PARAMS but with min1 much higher so v1_hat < min1.
    # GT_PARAMS: v1_hat ≈ (7/9)*6 / (0.5+0.5*2/9) = (42/9)/((4.5+1)/9)=(42/9)/(5.5/9)=42/5.5≈7.64
    # To make it out-of-support set min1=8 (v1_hat≈7.64 < 8).
    # But then v1_star=(6-3)/0.5=6 must still be in (8,10)? NO, 6<8 fails v1_star_in_support.
    # Need to adjust: keep v1_star in support but make v1_hat outside.
    # Let's use different params where v1_star is in support but v1_hat is not.
    # min1=1,max1=10,min2=1,max2=10, p=0.5, a1=3,a2=4,c1=6,c2=5.5 -> v1_hat≈7.64 in (1,10) IN support
    # To push v1_hat > max1=10: increase c1 while keeping v1_star in support.
    # v1_star=(c1-3)/0.5 in (1,10) => 3.5<c1<8. v1_hat=(1-f2)*c1/(0.5+0.5*f2).
    # f2=2/9, v1_hat=(7/9)*c1/(5.5/9)=7c1/5.5. For v1_hat>10: c1>10*5.5/7≈7.86. But c1<8.
    # c1=7.9: v1_star=(7.9-3)/0.5=9.8 in (1,10) OK; v1_hat=7*7.9/5.5≈10.05>10 OUT of support!
    # p*max1-c1=5-7.9=-2.9<0 OK; (1-p)*max2-c2=5-5.5=-0.5<0 OK; c1>a1=3 OK
    params = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=4, c1=7.9, c2=5.5, p=0.5)
    result = evaluate_case(params)
    assert result.branch.scenario == "GT"
    assert result.summary.status == "solver_no_valid_solution"
    assert result.summary.status_detail == "gt_candidate_out_of_support"
    assert result.solutions[0].in_support is False
    assert result.summary.valid_solution_count == 0


def test_gt_invalid_denominator():
    # denominator = p + (1-p)*F2(v2_star). Force F2(v2_star)→ some value so denom→0.
    # denom = p + (1-p)*f2 = 0 => f2 = -p/(1-p) which is negative, can't achieve normally.
    # Use extremely small denom_eps override: impossible to make denom truly 0 with valid params.
    # Instead test by patching: use custom Options with large denom_eps so it trips.
    # denom = p + (1-p)*f2. With p=0.5, f2=2/9: denom = 0.5 + 0.5*2/9 ≈ 0.611.
    # Set denom_eps=1.0 to force the guard.
    opts = Options(denom_eps=1.0)
    result = evaluate_case(GT_PARAMS, opts)
    assert result.branch.scenario == "GT"
    assert result.summary.status_detail == "gt_invalid_denominator"
    assert result.solutions == ()
    assert result.summary.status == "solver_no_valid_solution"
