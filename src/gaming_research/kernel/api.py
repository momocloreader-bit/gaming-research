from __future__ import annotations

from gaming_research.kernel.bluffing import solve_compat, solve_research
from gaming_research.kernel.gt import solve_gt
from gaming_research.kernel.types import Branch, KernelResult, Options, Params, Summary, Validation
from gaming_research.kernel.validation import validate


def evaluate_case(params: Params, options: Options | None = None) -> KernelResult:
    if options is None:
        options = Options()

    validation, derived = validate(params, options)

    if not validation.passed:
        summary = Summary(
            status="validation_failed",
            status_detail=", ".join(validation.failure_codes),
            valid_solution_count=0,
            selected_solution_index=None,
        )
        return KernelResult(
            params=params,
            derived=derived,
            validation=validation,
            branch=None,
            solutions=(),
            summary=summary,
        )

    scenario = "GT" if derived.GT_condition else "bluffing"

    if scenario == "GT":
        branch = Branch(scenario="GT", solver_mode="closed_form")
        solutions, status_detail = solve_gt(params, derived, options)
    else:
        solver_mode = options.bluffing_solver_mode
        branch = Branch(scenario="bluffing", solver_mode=solver_mode)
        if solver_mode == "compat":
            solutions, status_detail = solve_compat(params, derived, options)
        else:
            solutions, status_detail = solve_research(params, derived, options)

    valid_solutions = [s for s in solutions if s.in_support]
    valid_count = len(valid_solutions)

    if valid_count == 0:
        status = "solver_no_valid_solution"
        selected_index = None
    else:
        status = "solver_has_valid_solution"
        if scenario == "GT":
            selected_index = valid_solutions[0].root_index
        elif options.bluffing_solver_mode == "compat":
            selected_index = valid_solutions[0].root_index
        else:
            # research: smallest v1_hat in-support root
            smallest = min(valid_solutions, key=lambda s: s.v1_hat)
            selected_index = smallest.root_index

    summary = Summary(
        status=status,
        status_detail=status_detail,
        valid_solution_count=valid_count,
        selected_solution_index=selected_index,
    )

    return KernelResult(
        params=params,
        derived=derived,
        validation=validation,
        branch=branch,
        solutions=solutions,
        summary=summary,
    )
