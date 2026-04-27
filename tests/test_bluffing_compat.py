import pytest

from gaming_research.kernel import Options, Params, evaluate_case


# Bluffing params from test_validation: VALID_PARAMS triggers bluffing.
# min1=1,max1=10,min2=1,max2=10,a1=3,a2=3,c1=6,c2=6,p=0.5
# GT_rhs=2.4, v1_star=6 > 2.4 => bluffing
BLUFF_PARAMS = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)
COMPAT_OPTS = Options(bluffing_solver_mode="compat")


def test_compat_branch_selected():
    result = evaluate_case(BLUFF_PARAMS, COMPAT_OPTS)
    assert result.validation.passed is True
    assert result.branch.scenario == "bluffing"
    assert result.branch.solver_mode == "compat"


def test_compat_converges_to_one_solution():
    result = evaluate_case(BLUFF_PARAMS, COMPAT_OPTS)
    assert len(result.solutions) == 1
    sol = result.solutions[0]
    assert sol.source == "bluffing"
    assert sol.root_kind == "numerical"
    assert sol.root_index == 0


def test_compat_m_star_populated():
    result = evaluate_case(BLUFF_PARAMS, COMPAT_OPTS)
    sol = result.solutions[0]
    assert sol.m_star is not None
    # m_star = F2(v2_star)*v1_star + (1-F2(v2_star))*(-a1)
    d = result.derived
    expected_m_star = d.F2_v2_star * d.v1_star + (1 - d.F2_v2_star) * (-3.0)
    assert sol.m_star == pytest.approx(expected_m_star, rel=1e-9)


def test_compat_support_flags():
    result = evaluate_case(BLUFF_PARAMS, COMPAT_OPTS)
    sol = result.solutions[0]
    min1, max1 = 1.0, 10.0
    min2, max2 = 1.0, 10.0
    assert sol.in_support == (min1 <= sol.v1_hat <= max1 and min2 <= sol.v2_hat <= max2)


def test_compat_f1_f2_populated():
    result = evaluate_case(BLUFF_PARAMS, COMPAT_OPTS)
    sol = result.solutions[0]
    expected_f1 = (sol.v1_hat - 1.0) / (10.0 - 1.0)
    expected_f2 = (sol.v2_hat - 1.0) / (10.0 - 1.0)
    assert sol.F1_v1_hat == pytest.approx(expected_f1, rel=1e-9)
    assert sol.F2_v2_hat == pytest.approx(expected_f2, rel=1e-9)


def test_compat_numerical_failure():
    # Force fsolve to fail by setting denom_eps very large so the residual is always nan.
    # With denom_eps=1e10, the denominator guard always trips => residual always nan.
    # fsolve on an all-nan residual should fail or return a bad convergence flag.
    opts = Options(bluffing_solver_mode="compat", denom_eps=1e10)
    result = evaluate_case(BLUFF_PARAMS, opts)
    assert result.branch.scenario == "bluffing"
    assert result.summary.status_detail == "bluffing_numerical_failure"
    assert result.solutions == ()
    assert result.summary.status == "solver_no_valid_solution"
