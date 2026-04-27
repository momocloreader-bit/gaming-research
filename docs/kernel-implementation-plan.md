# Kernel Implementation Plan

## Purpose
This document records the concrete implementation decisions for the **first phase** of `gaming-research`. It sits one level below `core-kernel-design.md`: the contract document defines *what* the kernel must produce, and this plan fixes *how* it will be built.

The first phase is intentionally limited to the pure computation kernel. Exhaustion parsing, batch execution, summary writers, and any CLI are out of scope here and will be planned separately once the kernel is stable.

## Locked Implementation Decisions
- Package layout: `src/gaming_research/` with submodule split.
- Result schema: frozen `@dataclass` objects; serialization is the caller's responsibility via `dataclasses.asdict`.
- Numeric type policy: kernel input accepts `Decimal` or `float`; numerical solving uses `float` internally; the original numeric values are echoed unchanged in `KernelResult.params`.
- bluffing solving: both `compat` and `research` modes shipped together in this phase.
- bluffing `research` strategy: coarse equidistant sampling on `[min1, max1]` + sign-change bracket detection + `scipy.optimize.brentq` per bracket + tolerance-based deduplication.
- Tests: `pytest` covering validation paths, GT closed form, bluffing `compat` single-root, bluffing `research` zero / single / multi-root, and support boundary cases.

These decisions take precedence over any earlier informal notes.

## Package Layout
```
src/
  gaming_research/
    __init__.py           # public re-exports
    kernel/
      __init__.py         # re-exports evaluate_case + result types
      api.py              # evaluate_case orchestration
      types.py            # all frozen dataclasses
      validation.py       # input validation + failure codes
      derived.py          # v1_star, v2_star, F1/F2, GT_rhs, GT_condition
      gt.py               # GT closed-form solver
      bluffing.py         # residual function + compat + research solvers
tests/
  test_validation.py
  test_gt.py
  test_bluffing_compat.py
  test_bluffing_research.py
  test_evaluate_case.py
pyproject.toml            # hatchling backend, Python 3.11+, scipy + pytest deps
```
No CLI, no `results/`, no exhaustion parser modules in this phase.

## Result Schema
All result objects are `@dataclass(frozen=True)`. The kernel itself does not serialize anything; downstream callers convert with `dataclasses.asdict` when writing CSV / JSON.

### Top-level
```python
@dataclass(frozen=True)
class KernelResult:
    params: Params
    derived: Derived | None         # None when validation fails before computation
    validation: Validation
    branch: Branch | None           # None when validation fails
    solutions: tuple[Solution, ...] # empty tuple means no candidate produced
    summary: Summary
```

### Sections
- `Params`: echoed normalized inputs `(min1, max1, min2, max2, a1, a2, c1, c2, p)`. Each field stores the value as supplied by the caller (`Decimal` or `float`); the kernel does not silently coerce types stored here.
- `Derived`: `v1_star, v2_star, F1_v1_star, F2_v2_star, one_minus_F1_v1_star, one_minus_F2_v2_star, GT_rhs, GT_condition` (all `float`).
- `Validation`: `passed: bool`, `failure_codes: tuple[str, ...]`, `failure_messages: tuple[str, ...]`.
- `Branch`: `scenario: Literal["GT", "bluffing"]`, `solver_mode: Literal["closed_form", "compat", "research"]`.
- `Solution`: `source, root_kind, root_index, v1_hat, v2_hat, in_support, F1_v1_hat, F2_v2_hat, m_star: float | None`.
- `Summary`: `status, status_detail, valid_solution_count, selected_solution_index: int | None`.

`solutions` is a tuple to preserve ordering and immutability.

## Numeric Type Policy
- The public entry point accepts `Params` whose numeric fields may be `Decimal` or `float`. This matches the upstream exhaustion enumerator that will use `Decimal` to avoid `0.1` floating-point drift.
- All numerical computation (CDF evaluations, GT closed form, bluffing residual, `brentq`) operates on `float`. Conversion happens at the boundary of `derived.py` and once at the boundary of each solver, never silently inside math expressions.
- The original numeric values supplied by the caller are stored unchanged in `KernelResult.params`. Downstream summary writers may format them however they need.

## Options Surface

### Python and build
- Target Python: **3.11+**. The schema relies on PEP 604 unions (`A | B`), `Literal[...]`, and built-in generics (`tuple[...]`, `Mapping[...]`).
- Build backend: **hatchling**. `pyproject.toml` declares only `scipy` and `pytest` as dependencies in this phase.

### Validation message language
`failure_messages` are **English-only** in this phase. The `failure_codes` are language-neutral identifiers and constitute the stable contract; downstream tooling that needs another language must map by code, not by parsing message text.

### Options dataclass
This is the full, locked shape of `Options`. Field names and defaults are fixed; do not rename or reorder them.

```python
@dataclass(frozen=True)
class Options:
    # validation toggles
    enforce_war_payoff_s1: bool = True
    enforce_war_payoff_s2: bool = True
    # bluffing solver selection
    bluffing_solver_mode: Literal["compat", "research"] = "research"
    # research-mode tuning
    bluffing_sample_count: int = 200
    xtol: float = 1e-12
    rtol: float = 8.881784197001252e-16   # 4 * sys.float_info.epsilon
    zero_tol: float = 1e-9
    dedup_tol: float = 1e-6
    # universal numerical guard (shared by GT and bluffing)
    denom_eps: float = 1e-12
```

`evaluate_case(params, options=None)` treats `options is None` as `Options()`.

### Where each option is applied
- `denom_eps`: GT denominator guard, bluffing `expr2` denominator guard inside the residual, and any other near-zero-divisor check. The single epsilon is reused everywhere so behavior is consistent across solvers.
- `bluffing_sample_count`, `xtol`, `rtol`, `zero_tol`, `dedup_tol`: research mode only; compat mode does not consult them.
- `enforce_war_payoff_s1` / `enforce_war_payoff_s2`: validation only. When `False`, the corresponding rule is skipped entirely and never appears in `failure_codes` or `failure_messages`.
- `bluffing_solver_mode`: read once at branch dispatch and stored in `Branch.solver_mode`.

## Validation
Implemented in `kernel/validation.py`. Each rule has a stable code string and a human-readable message. Codes (matching `core-kernel-design.md`):

- `all_positive`
- `min1_lt_max1`
- `min2_lt_max2`
- `p_in_open_unit_interval`
- `c1_gt_a1`
- `c2_gt_a2`
- `v1_star_in_support`
- `v2_star_in_support`
- `s1_war_payoff_negative`  (i.e. `p * max1 - c1 < 0`)
- `s2_war_payoff_negative`  (i.e. `(1 - p) * max2 - c2 < 0`)

Failure short-circuits the pipeline:
- `Validation.passed = False`.
- `derived` may still be partially filled (`v1_star`, `v2_star`) when those values are needed for the failure messages, but the kernel must not run any solver.
- `summary.status = "validation_failed"`; `summary.status_detail` lists the failed codes joined in stable order.

The two war-payoff rules are gated by `Options.enforce_war_payoff_s1` / `Options.enforce_war_payoff_s2` (default `True`). When disabled, the corresponding code is skipped entirely and never appears in `failure_codes` or `failure_messages`. This is the rule-toggle hook that the exhaustion layer will eventually use.

## GT Solver (`kernel/gt.py`)
Closed form, exactly as described in `current-program-algorithm.md`:

- `denominator = p + (1 - p) * F2(v2_star)`
- if `abs(denominator) < options.denom_eps`: **emit zero solutions**; `status_detail = gt_invalid_denominator`.
- else compute:
  - `v1_hat = ((1 - F2(v2_star)) * c1) / denominator`
  - `v2_hat = v2_star`
  - `in_support = (min1 <= v1_hat <= max1) and (min2 <= v2_hat <= max2)`

GT **always emits exactly one `Solution`** when the denominator guard passes, regardless of `in_support`. The support flag lives on the `Solution` itself; it does not gate solution emission. Only the invalid-denominator branch produces zero solutions.

The single emitted `Solution` carries `source="GT"`, `root_kind="closed_form"`, `root_index=0`, `m_star=None`.

Status detail values (mutually exclusive):
- `gt_valid_solution`            — denominator OK, `in_support=True`, one `Solution`
- `gt_candidate_out_of_support`  — denominator OK, `in_support=False`, one `Solution`
- `gt_invalid_denominator`       — denominator guard tripped, zero solutions

## Bluffing Solver (`kernel/bluffing.py`)

### Residual Function
Re-derived from the math described in `current-program-algorithm.md` (sections "Bluffing Expression 1" / "Bluffing Expression 2"). The kernel does **not** import or shell out to the legacy `gaming1030.py`, does **not** capture stdout, and does **not** regex any text.

For a candidate `v1_hat`:

- `expr1(v1_hat) = min2 + (max2 - min2) * (a1 / (v1_hat + a1))`
- `numerator   = (max1 - min1) * (1 - F1(v1_star)) * c2 - (max1 - v1_hat) * a2`
- `denominator = (max1 - v1_hat) - (max1 - min1) * p * (1 - F1(v1_star))`
- `expr2(v1_hat) = numerator / denominator`. When `abs(denominator) < options.denom_eps`, the residual is **undefined** at that `v1_hat`: it is a discontinuity, not a root. Discontinuities are excluded from sign-change detection in research mode, and trigger `bluffing_numerical_failure` in compat mode if `fsolve` happens to converge onto one.
- `residual(v1_hat) = expr1(v1_hat) - expr2(v1_hat)` (undefined when the guard above trips)

The residual is exposed as a pure factory `build_residual(params, derived) -> Callable[[float], float]` so both solver modes share it without code duplication.

### `compat` mode
Mirrors the current single-run program:

- one initial guess `v1_init = (min1 + max1) / 2`
- `scipy.optimize.fsolve(residual, v1_init, full_output=True)`
- if convergence flag indicates failure: return zero solutions; status detail `bluffing_numerical_failure`
- otherwise: build one `Solution` from the resulting `v1_hat` regardless of support; set `in_support` accordingly
- at most one `Solution`; `root_kind="numerical"`, `root_index=0`

### `research` mode
- coarse sampling: `N = options.bluffing_sample_count` points (default `200`) equally spaced on `[min1, max1]`
- evaluate `residual` at each sample, skipping points where `abs(denominator) < options.denom_eps`; those points are recorded as discontinuities, not as roots
- for each adjacent pair of finite samples whose residuals have opposite signs, call `brentq(residual, lo, hi, xtol=options.xtol, rtol=options.rtol)`
- additionally, treat any sample whose `|residual|` is below `options.zero_tol` as a candidate root directly (subject to deduplication)
- deduplicate candidate roots by `|v1_a - v1_b| <= options.dedup_tol` (default `1e-6`)
- the returned `Solution` list contains every accepted root in ascending `v1_hat` order, with `root_index = 0..k-1`

The numeric tunables consumed by research mode (`bluffing_sample_count`, `xtol`, `rtol`, `zero_tol`, `dedup_tol`) are defined once on `Options` (see "Options Surface" above). They must not be hard-coded inside the solver.

### Per-root post-processing (both modes)
For every accepted `v1_hat`:

- `v2_hat = expr1(v1_hat)`
- `F1_v1_hat = (v1_hat - min1) / (max1 - min1)`
- `F2_v2_hat = (v2_hat - min2) / (max2 - min2)`
- `m_star   = F2(v2_star) * v1_star + (1 - F2(v2_star)) * (-a1)`
- `in_support = (min1 <= v1_hat <= max1) and (min2 <= v2_hat <= max2)`

`m_star` is computed once per case from derived quantities and attached to every bluffing `Solution`, including out-of-support candidates, because it is a branch-derived quantity that does not depend on which root is selected.

### Status detail values
- `bluffing_no_root_found`
- `bluffing_root_found_but_out_of_support`
- `bluffing_single_valid_root`
- `bluffing_multiple_valid_roots`
- `bluffing_numerical_failure`

## Branch Decision and Summary Mapping
After validation passes:

- `GT_condition = (v1_star <= GT_rhs)`; `True` means `scenario = "GT"`, `False` means `scenario = "bluffing"`.
- `solver_mode` is `"closed_form"` for GT, and `options.bluffing_solver_mode` (`"compat"` or `"research"`, default `"research"`) for bluffing.
- `summary.valid_solution_count` = number of `Solution` entries with `in_support == True`.
- `summary.selected_solution_index`:
  - GT: index of the single (in-support) solution if any, else `None`.
  - bluffing `compat`: same rule.
  - bluffing `research`: index of the smallest-`v1_hat` in-support root if at least one exists, else `None`.
  - The "primary root" rule is intentionally simple here; downstream layers may override it later without changing the kernel.
- `summary.status` mapping:
  - validation failed -> `validation_failed`
  - GT in-support -> `solver_has_valid_solution`
  - GT out-of-support or invalid denominator -> `solver_no_valid_solution`
  - bluffing with zero roots -> `solver_no_valid_solution`
  - bluffing with at least one in-support root -> `solver_has_valid_solution`
  - bluffing with roots that all fall outside support -> `solver_no_valid_solution`
- `summary.status_detail` carries the more granular code listed under each solver above.

## Tests
`pytest` under top-level `tests/`. Each test imports only from the public package boundary `gaming_research.kernel`.

Required cases for the first phase:

- `test_validation.py`: each failure code triggered in isolation; option flags disable the two war-payoff codes; passing inputs report `passed=True` with empty failure tuples.
- `test_gt.py`: a parameter set satisfying `GT_condition`; verify closed-form `v1_hat` matches the formula and `v2_hat == v2_star`; an out-of-support GT case yields `solver_no_valid_solution` with `gt_candidate_out_of_support`; an invalid-denominator case yields `gt_invalid_denominator`.
- `test_bluffing_compat.py`: a known bluffing parameter set converges to one `v1_hat`; assert support flags and `m_star` populated; a crafted numerical-failure case returns `bluffing_numerical_failure` and zero solutions.
- `test_bluffing_research.py`: a synthetic case with at least two sign changes in the residual sample produces multiple `Solution` entries; a zero-root case returns an empty `solutions` tuple; deduplication merges two near-equal roots into one; out-of-support roots are retained in `solutions` but excluded from `valid_solution_count`.
- `test_evaluate_case.py`: end-to-end smoke for both branches and both bluffing modes; serialize the result through `asdict` and assert that all six top-level sections are present and contain the expected keys.

Numerical assertions use `pytest.approx` aligned with the kernel-default tolerances.

## Out of Scope (Deferred)
The following are explicitly not part of this phase:

- exhaustion spec parsing for `docs/exhaustion.txt`
- analytic domain reduction enumerator (35 * 7 * 4 * 4 = 3920)
- batch runner and `results/exhaustion/` artifacts (`cases.csv`, `summary.csv`, `summary.md`, `metadata.json`)
- CLI module
- any UI-oriented compatibility wrapper or `audit.txt` / `audit_display.json` mapping

These remain tracked by `exhaustion-design.md` and `core-kernel-design.md`, and will be planned in a follow-up document once the kernel passes its tests.
