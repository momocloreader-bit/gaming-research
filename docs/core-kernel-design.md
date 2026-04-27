# Core Kernel Design

## Purpose
This document defines the pure computation kernel that should become the foundation of the research repository.

The kernel must evaluate one parameter case and return a structured result without any CLI, UI, filesystem, or text-parsing side effects.

## Design Goals
- One input case in, one structured result out
- No file writes
- No printing
- No `input()`
- No dependence on `audit.txt` / `audit_display.json`
- No dependence on capturing `stdout` from other scripts
- Preserve enough detail for both batch research and future thin wrappers

## Locked Decisions
The following decisions are fixed for this repository phase:

- `summary.status` and `summary.status_detail` will use research-oriented classification rather than legacy UI-oriented simplification.
- bluffing solving will support two modes: `compat` and `research`.
- the kernel must preserve multiple roots in `solutions`; it must not collapse them to a single solution at kernel level.
## Proposed Entry Point
Logical shape:

- `evaluate_case(params, options=None) -> result`

## Input Contract
`params` should include:

- `min1,max1,min2,max2,a1,a2,c1,c2,p`

`options` should reserve at least:

- whether to enforce `p*max1-c1<0`
- whether to enforce `(1-p)*max2-c2<0`
- bluffing solver mode: `compat` or `research` (fixed design decision)
- numeric tolerances

## Output Contract
The kernel result should contain six sections:

1. `params`
2. `derived`
3. `validation`
4. `branch`
5. `solutions`
6. `summary`

### `params`
Echoed normalized inputs.

### `derived`
Should include at least:

- `v1_star`
- `v2_star`
- `F1(v1_star)`
- `F2(v2_star)`
- `1-F1(v1_star)`
- `1-F2(v2_star)`
- `GT_rhs`
- `GT_condition`

### `validation`
Should include:

- `passed`
- `failure_codes`
- `failure_messages`

Validation failures should be recorded in a machine-readable form, not only as display text.

### `branch`
Should include:

- `scenario`: `GT` or `bluffing`
- `solver_mode`

### `solutions`
Should be a list, not a single pair of values.

Each solution candidate should include at least:

- `source`: `GT` or `bluffing`
- `root_kind`: `closed_form` or `numerical`
- `root_index`
- `v1_hat`
- `v2_hat`
- `in_support`
- `F1(v1_hat)`
- `F2(v2_hat)`
- `m_star` when applicable

### `summary`
Should include:

- `status`
- `status_detail`
- `valid_solution_count`
- `selected_solution_index`

The summary should be a classification layer over the underlying detailed candidates.

## Full Execution Flow

### 1. Normalize Inputs
- Check that all required keys exist
- Normalize numeric types
- Allow upstream range generation to use `Decimal`, but the kernel may convert to float for numerical solving

### 2. Compute Derived Quantities
Compute first:

- `v1_star = (c1 - a1) / p`
- `v2_star = (c2 - a2) / (1 - p)`
- `F1(v1_star)`
- `F2(v2_star)`
- `1-F1(v1_star)`
- `1-F2(v2_star)`
- `GT_rhs = ((1 - F2(v2_star)) * a1) / F2(v2_star)`
- `GT_condition`

### 3. Validate Inputs
Validation should produce both codes and messages.

Suggested codes:

- `all_positive`
- `min1_lt_max1`
- `min2_lt_max2`
- `p_in_open_unit_interval`
- `c1_gt_a1`
- `c2_gt_a2`
- `v1_star_in_support`
- `v2_star_in_support`
- `s1_war_payoff_negative`
- `s2_war_payoff_negative`

If validation fails:

- stop before branch solving
- return `summary.status = validation_failed`

### 4. Determine Scenario
If validation passes:

- `GT_condition = true` -> `scenario = GT`
- otherwise -> `scenario = bluffing`

### 5. Solve GT Case
GT solving is closed-form.

Compute:

- `v1_hat = ((1 - F2(v2_star)) * c1) / (p + (1 - p) * F2(v2_star))`
- `v2_hat = v2_star`

Then derive:

- `F1(v1_hat)`
- `F2(v2_hat)`
- support inclusion checks

GT should produce either zero or one candidate solution object.

Suggested GT status details:

- `gt_valid_solution`
- `gt_candidate_out_of_support`
- `gt_invalid_denominator`

## 6. Solve Bluffing Case
Bluffing should be handled as a pure residual function plus a solver policy.

### Residual Function
Construct a pure residual function of `v1_hat` whose root corresponds to the equilibrium condition.

This logic should be extracted from the current `gaming1030.py` math, not from its text output.

### Solver Modes
#### `compat`
- behavior intended to stay close to the current single-run program
- one midpoint-style numerical attempt
- at most one candidate returned

#### `research`
- sample the interval `[min1, max1]`
- detect near-zero points and sign-change brackets
- solve each bracket separately
- de-duplicate repeated roots
- return all candidate roots

### For Each Bluffing Root
For every root found:

- compute `v2_hat`
- compute `F1(v1_hat)`
- compute `F2(v2_hat)`
- compute `m_star`
- mark `in_support`

Suggested bluffing status details:

- `bluffing_no_root_found`
- `bluffing_root_found_but_out_of_support`
- `bluffing_single_valid_root`
- `bluffing_multiple_valid_roots`
- `bluffing_numerical_failure`

## m_star Placement
`m_star` should be treated as part of the branch result model, not as a side calculation hidden in a wrapper.

Current formula:

- `m_star = F2(v2_star) * v1_star + (1 - F2(v2_star)) * (-a1)`

It should be present in bluffing results even when no valid root is ultimately selected, because it is a branch-derived quantity.

## Layering Around The Kernel
The repository should conceptually separate three layers:

1. pure computation kernel
2. single-case wrapper(s) for CLI / compatibility use
3. batch exhaustion runner

The kernel owns the mathematics.
The wrappers own presentation, files, and compatibility mapping.

## Why The Kernel Must Return A Solution List
For research, one parameter set may need to preserve:

- no root
- one root
- multiple roots
- roots outside support

If the kernel collapses everything too early into one `v1_hat,v2_hat`, the later exhaustion analysis loses information.

Therefore:

- the kernel should preserve all candidates
- upper layers may later choose a primary solution if needed

## Recommended Default Policy
For future implementation:

- keep the kernel detailed and research-oriented
- preserve multiple roots when found
- let compatibility wrappers map the result to simpler statuses when needed


