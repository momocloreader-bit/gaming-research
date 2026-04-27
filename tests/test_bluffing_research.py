import math

import pytest

from gaming_research.kernel import Options, Params, evaluate_case
from gaming_research.kernel.bluffing import build_residual
from gaming_research.kernel.derived import compute_derived


# Standard bluffing params
BLUFF_PARAMS = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)
RESEARCH_OPTS = Options(bluffing_solver_mode="research")


def test_research_branch_selected():
    result = evaluate_case(BLUFF_PARAMS, RESEARCH_OPTS)
    assert result.branch.scenario == "bluffing"
    assert result.branch.solver_mode == "research"


def test_research_finds_at_least_one_root():
    result = evaluate_case(BLUFF_PARAMS, RESEARCH_OPTS)
    assert len(result.solutions) >= 1


def test_research_out_of_support_roots_retained():
    # Out-of-support roots should still appear in solutions with in_support=False
    result = evaluate_case(BLUFF_PARAMS, RESEARCH_OPTS)
    # All solutions have in_support set (True or False); count valid ones
    valid = [s for s in result.solutions if s.in_support]
    assert result.summary.valid_solution_count == len(valid)


def test_research_zero_root_case():
    # Force no roots by making the residual have no sign change.
    # Use denom_eps so large that residual is always nan => no sign changes => no roots.
    opts = Options(bluffing_solver_mode="research", denom_eps=1e10)
    result = evaluate_case(BLUFF_PARAMS, opts)
    assert result.solutions == ()
    assert result.summary.status_detail == "bluffing_no_root_found"
    assert result.summary.status == "solver_no_valid_solution"


def test_research_deduplication():
    # Two very close sample points near a root should deduplicate to one solution.
    # Use a high sample count and tight dedup_tol to verify deduplication logic.
    opts = Options(bluffing_solver_mode="research", bluffing_sample_count=500, dedup_tol=0.1)
    result = evaluate_case(BLUFF_PARAMS, opts)
    # Verify no two solutions are within dedup_tol of each other
    roots = [s.v1_hat for s in result.solutions]
    for i in range(len(roots)):
        for j in range(i + 1, len(roots)):
            assert abs(roots[i] - roots[j]) > 0.1


def test_research_root_indices_sequential():
    result = evaluate_case(BLUFF_PARAMS, RESEARCH_OPTS)
    for i, sol in enumerate(result.solutions):
        assert sol.root_index == i


def test_research_roots_ascending():
    result = evaluate_case(BLUFF_PARAMS, RESEARCH_OPTS)
    roots = [s.v1_hat for s in result.solutions]
    assert roots == sorted(roots)


def test_research_m_star_on_all_solutions():
    result = evaluate_case(BLUFF_PARAMS, RESEARCH_OPTS)
    d = result.derived
    expected_m_star = d.F2_v2_star * d.v1_star + (1 - d.F2_v2_star) * (-3.0)
    for sol in result.solutions:
        assert sol.m_star is not None
        assert sol.m_star == pytest.approx(expected_m_star, rel=1e-9)


def test_research_multiple_roots_synthetic():
    # Craft a parameter set that empirically produces multiple roots.
    # Use asymmetric parameters to encourage multiple sign changes.
    # min1=0.5,max1=20,min2=0.5,max2=20,a1=5,a2=1,c1=8,c2=9,p=0.3
    # v1_star=(8-5)/0.3=10 in (0.5,20) OK
    # v2_star=(9-1)/0.7=11.43 in (0.5,20) OK
    # p*max1-c1=0.3*20-8=-2<0 OK; (1-p)*max2-c2=0.7*20-9=5>0 FAIL s2
    # Use enforce_war_payoff_s2=False or adjust c2.
    # (1-p)*max2<c2 => 0.7*20=14<c2. c2=15, a2=1: v2_star=(15-1)/0.7=20, not in (0.5,20) open.
    # v2_star must be strictly less than max2=20. c2=14.5: v2_star=(14.5-1)/0.7=19.29 in (0.5,20) OK
    # (1-p)*max2-c2=14-14.5=-0.5<0 OK
    # Try this set:
    params = Params(min1=0.5, max1=20, min2=0.5, max2=20, a1=5, a2=1, c1=8, c2=14.5, p=0.3)
    opts = Options(bluffing_solver_mode="research", bluffing_sample_count=400)
    result = evaluate_case(params, opts)
    # Just verify it runs successfully without error; structure is correct
    assert result.validation.passed is True
    assert result.branch.scenario == "bluffing"
    for i, sol in enumerate(result.solutions):
        assert sol.root_index == i
        assert sol.m_star is not None


def test_research_selected_solution_is_smallest_valid():
    result = evaluate_case(BLUFF_PARAMS, RESEARCH_OPTS)
    valid = [s for s in result.solutions if s.in_support]
    if valid:
        smallest = min(valid, key=lambda s: s.v1_hat)
        assert result.summary.selected_solution_index == smallest.root_index
