import dataclasses

import pytest

from gaming_research.kernel import Options, Params, evaluate_case

# GT params: min1=1,max1=10,min2=1,max2=10,a1=3,a2=4,c1=6,c2=5.5,p=0.5
GT_PARAMS = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=4, c1=6, c2=5.5, p=0.5)

# Bluffing params: min1=1,max1=10,min2=1,max2=10,a1=3,a2=3,c1=6,c2=6,p=0.5
BLUFF_PARAMS = Params(min1=1, max1=10, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)


def _top_level_keys(result):
    return set(dataclasses.asdict(result).keys())


def test_gt_end_to_end_structure():
    result = evaluate_case(GT_PARAMS)
    d = dataclasses.asdict(result)
    assert set(d.keys()) == {"params", "derived", "validation", "branch", "solutions", "summary"}


def test_gt_asdict_params_keys():
    result = evaluate_case(GT_PARAMS)
    d = dataclasses.asdict(result)
    assert set(d["params"].keys()) == {"min1", "max1", "min2", "max2", "a1", "a2", "c1", "c2", "p"}


def test_gt_asdict_derived_keys():
    result = evaluate_case(GT_PARAMS)
    d = dataclasses.asdict(result)
    assert set(d["derived"].keys()) == {
        "v1_star", "v2_star",
        "F1_v1_star", "F2_v2_star",
        "one_minus_F1_v1_star", "one_minus_F2_v2_star",
        "GT_rhs", "GT_condition",
    }


def test_gt_asdict_solution_keys():
    result = evaluate_case(GT_PARAMS)
    d = dataclasses.asdict(result)
    sol = d["solutions"][0]
    assert set(sol.keys()) == {
        "source", "root_kind", "root_index",
        "v1_hat", "v2_hat", "in_support",
        "F1_v1_hat", "F2_v2_hat", "m_star",
    }


def test_gt_asdict_summary_keys():
    result = evaluate_case(GT_PARAMS)
    d = dataclasses.asdict(result)
    assert set(d["summary"].keys()) == {
        "status", "status_detail", "valid_solution_count", "selected_solution_index"
    }


def test_bluffing_research_end_to_end():
    opts = Options(bluffing_solver_mode="research")
    result = evaluate_case(BLUFF_PARAMS, opts)
    assert result.validation.passed is True
    assert result.branch.scenario == "bluffing"
    assert result.branch.solver_mode == "research"
    d = dataclasses.asdict(result)
    assert set(d.keys()) == {"params", "derived", "validation", "branch", "solutions", "summary"}


def test_bluffing_compat_end_to_end():
    opts = Options(bluffing_solver_mode="compat")
    result = evaluate_case(BLUFF_PARAMS, opts)
    assert result.validation.passed is True
    assert result.branch.scenario == "bluffing"
    assert result.branch.solver_mode == "compat"
    d = dataclasses.asdict(result)
    assert set(d.keys()) == {"params", "derived", "validation", "branch", "solutions", "summary"}


def test_bluffing_asdict_solution_has_m_star():
    opts = Options(bluffing_solver_mode="compat")
    result = evaluate_case(BLUFF_PARAMS, opts)
    d = dataclasses.asdict(result)
    if d["solutions"]:
        assert "m_star" in d["solutions"][0]
        assert d["solutions"][0]["m_star"] is not None


def test_none_options_defaults():
    result = evaluate_case(GT_PARAMS, None)
    assert result.branch is not None


def test_validation_failed_asdict():
    bad_params = Params(min1=10, max1=5, min2=1, max2=10, a1=3, a2=3, c1=6, c2=6, p=0.5)
    result = evaluate_case(bad_params)
    d = dataclasses.asdict(result)
    assert d["summary"]["status"] == "validation_failed"
    assert d["branch"] is None
    assert d["solutions"] == ()


def test_params_echoed_unchanged():
    result = evaluate_case(GT_PARAMS)
    assert result.params is GT_PARAMS
