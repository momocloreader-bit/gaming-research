# Current Program Algorithm, Flow, and Framework

## Purpose
This document describes the current `gaming` program as it exists today in the UI-oriented repository.

It is intentionally different from `core-kernel-design.md`:

- this document describes the current implementation
- `core-kernel-design.md` describes the target pure computation design for the research repository

The goal is to preserve a clear record of the existing algorithm, execution flow, and module coupling before refactoring begins.

## Current Repository-Level Structure
The current program is functionally split across four main scripts:

- `main.py`: single-case orchestration, validation, branch dispatch, result aggregation, file output
- `gt.py`: closed-form GT branch computation
- `gaming1030.py`: bluffing branch numerical solving script
- `ui.py`: PySide6 interface that calls `main.run_calculation(...)`

The current system therefore has one computational center (`main.py`) plus two branch implementations and one presentation layer.

## Current Mathematical Definitions
For one parameter set:

- `v1_star = (c1 - a1) / p`
- `v2_star = (c2 - a2) / (1 - p)`

Uniform CDF definitions:

- `F1(v) = (v - min1) / (max1 - min1)`
- `F2(v) = (v - min2) / (max2 - min2)`

These quantities are used for both validation and branch classification.

## Current Validation Logic In `main.py`
After parsing input, `main.py` computes `v1_star` and `v2_star`, then checks:

- all parameters are positive
- `min1 < max1`
- `min2 < max2`
- `0 < p < 1`
- `c1 > a1`
- `c2 > a2`
- `min1 < v1_star < max1`
- `min2 < v2_star < max2`
- `p * max1 - c1 < 0`
- `(1 - p) * max2 - c2 < 0`

When validation fails, `main.py` emits a list of failed constraints with formula text and Chinese interpretation, then stops before branch solving.

## Branch Classification Logic
If validation passes, `main.py` computes:

- `F2(v2_star)`
- `GT_rhs = ((1 - F2(v2_star)) * a1) / F2(v2_star)`

Then it classifies the case as:

- `GT` if `v1_star <= GT_rhs`
- `bluffing` otherwise

This branch selection is the central decision point of the current program.

## GT Branch: Current Algorithm
The GT branch is implemented in `gt.py` and called by `main.py`.

### Inputs Passed To `gt.py`
`main.py` passes:

- `F2(v2_star)`
- `c1`
- `p`
- `max1`
- `min1`
- `v2_star`

### Closed-Form Computation
`gt.py` computes:

- `denominator = p + (1 - p) * F2(v2_star)`
- `v1_hat = ((1 - F2(v2_star)) * c1) / denominator`
- `v2_hat = v2_star`

### GT Status In `gt.py`
`gt.py` currently assigns a local status based on `v1_hat`:

- invalid denominator
- `v1_hat <= min1`
- `max1 > v1_hat`
- `max1 <= v1_hat`

However, this local status is not the final program-level status.

### Final GT Status In `main.py`
`main.py` re-checks whether:

- `v1_hat` is in `[min1, max1]`
- `v2_hat` is in `[min2, max2]`

If both are in support:

- `status = solver_has_valid_solution`

Otherwise:

- `status = solver_no_valid_solution`

So the current program-level GT status is a support-based binary classification layered on top of `gt.py`'s local result.

## Bluffing Branch: Current Algorithm
The bluffing branch is implemented in `gaming1030.py`, but not as a pure function.

### Current Integration Style
`main.py` does not call a clean solver API.
Instead it:

1. monkey-patches `input()`
2. redirects `stdout`
3. executes `gaming1030.solve_for_v1_hat()`
4. captures the printed text
5. extracts `v1_hat` and `v2_hat` using regex

This is the most important coupling problem in the current architecture.

### Numerical Setup In `gaming1030.py`
`gaming1030.py` defines:

- `F1(v)`
- `F2(v)`
- `f1_of_v1_star = F1(v1_star)`
- `f2_of_v2_star = F2(v2_star)`

It then defines a residual equation in `v1_hat` by equating two expressions for `v2_hat`.

### Bluffing Expression 1
From the rearranged first equilibrium relation:

- `v2_hat = min2 + (max2 - min2) * (a1 / (v1_hat + a1))`

### Bluffing Expression 2
From the second equilibrium relation in the current script:

- numerator = `(max1 - min1) * (1 - F1(v1_star)) * c2 - (max1 - v1_hat) * a2`
- denominator = `(max1 - v1_hat) - (max1 - min1) * p * (1 - F1(v1_star))`
- `v2_hat = numerator / denominator`

### Bluffing Solve Procedure
The current script then:

- uses midpoint initial guess: `(min1 + max1) / 2`
- calls `scipy.optimize.fsolve`
- obtains one candidate `v1_hat`
- computes one derived `v2_hat` from expression 1

### Final Bluffing Status In `main.py`
`main.py` again performs the support check:

- `v1_hat` in `[min1, max1]`
- `v2_hat` in `[min2, max2]`

If valid:

- `status = solver_has_valid_solution`

Otherwise:

- `status = solver_no_valid_solution`

So, at the current program level, bluffing is also reduced to a binary support-based status.

## Current Derived Outputs
If the final status is valid, `main.py` computes:

- `F1(v1_hat)`
- `F2(v2_hat)`
- `1 - F1(v1_hat)`
- `1 - F2(v2_hat)`

If the case is bluffing and valid, `main.py` also computes:

- `m_star = F2(v2_star) * v1_star + (1 - F2(v2_star)) * (-a1)`
- `v1_hat_m = v1_star`
- `v2_hat_m = v2_star`

## Current Output Artifacts
The current single-case program writes two files:

- `results/audit.txt`
- `results/audit_display.json`

### `audit.txt`
Contains:

- inputs
- derived quantities
- branch choice
- final status
- selected solution values

### `audit_display.json`
Contains the same logical content in a UI-oriented, formatted representation.

## Current UI Framework Relationship
`ui.py` does not implement new mathematics.
It is a wrapper over `main.run_calculation(...)`.

The UI is responsible for:

- collecting inputs
- calling `main.run_calculation(...)`
- reading the returned payload
- displaying report pages
- rendering SVG diagrams with tagged parameter values

So the current UI layer is not independent from the algorithmic center; it is a consumer of the same orchestration function that also writes result files.

## Current Framework Summary
The current framework can be summarized as:

1. parse one case
2. validate inputs
3. classify GT vs bluffing
4. solve one branch
5. reduce result to a final binary support-validity status
6. write audit artifacts
7. optionally display the same result through the UI

This is workable for one-off runs, but it is not an ideal architecture for research, batch enumeration, or solver analysis.

## Main Architectural Limitations Of The Current Program
From a research and batch-analysis perspective, the current implementation has several limitations:

1. The computation core is mixed with file output.
2. The bluffing branch is integrated through console I/O emulation and regex parsing.
3. The final program status is overly compressed into a binary valid / invalid model.
4. Only one candidate bluffing root is attempted in the current single-run flow.
5. The same orchestration path is shared by CLI and UI, which makes research-side refactoring harder.

## Why This Matters For `gaming-research`
The new `gaming-research` repository is intended to separate:

- the mathematical / solver core
- the exhaustion / batch analysis layer
- any future visualization or reporting layer

This document therefore acts as the baseline description of the old system before the new pure computation architecture replaces it.
