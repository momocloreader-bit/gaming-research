# gaming-research

This repository is dedicated to the research-side core algorithm work that is being split out from the UI-oriented `gaming` repository.

## Scope
- Batch exhaustion / enumeration of parameter combinations
- Pure computation kernel shared by future batch tools
- Research-oriented solver behavior documentation
- Structured output planning for later analysis and visualization

## Initial Documents
- `docs/exhaustion.txt`: original exhaustion condition specification
- `docs/exhaustion-design.md`: batch exhaustion design
- docs/core-kernel-design.md: pure computation kernel design
- docs/current-program-algorithm.md: baseline description of the current gaming program's algorithm, execution flow, and framework
- docs/kernel-implementation-plan.md: concrete first-phase implementation plan for the kernel
- docs/loader-design.md: table-to-kernel input bridge design (next phase after the kernel)

## Non-Goals For This Repository Setup Phase
- No UI code
- No packaging scripts
- No runtime coupling to `audit.txt` / `audit_display.json`

## Kernel Integration Guide
<!-- Added 2026-04-27: Phase 1 (v1.0) complete -->

Install the package (Python 3.11+, requires `scipy`):

```bash
pip install -e .
```

Basic usage:

```python
from gaming_research.kernel import evaluate_case, Params, Options

params = Params(
    min1=1, max1=10,
    min2=1, max2=10,
    a1=3,  a2=3,
    c1=6,  c2=6,
    p=0.5,
)

result = evaluate_case(params)           # uses default Options
# or: result = evaluate_case(params, Options(bluffing_solver_mode="compat"))
```

Key fields on `KernelResult`:

| Field | Type | Notes |
|---|---|---|
| `result.validation.passed` | `bool` | `False` stops the pipeline; check `failure_codes` |
| `result.branch.scenario` | `"GT"` \| `"bluffing"` | branch taken |
| `result.solutions` | `tuple[Solution, ...]` | all roots, including out-of-support |
| `result.summary.status` | `str` | `solver_has_valid_solution`, `solver_no_valid_solution`, or `validation_failed` |
| `result.summary.selected_solution_index` | `int \| None` | index into `result.solutions`; `None` if no valid root |

Serialization — the kernel does not serialize; callers do:

```python
import dataclasses, json
d = dataclasses.asdict(result)
json.dumps(d)                            # all fields are JSON-serializable primitives
```

Numeric policy: `Params` fields accept `float` or `decimal.Decimal`; the original values are echoed unchanged in `result.params`. All internal math uses `float`.

Solver options (all have defaults; pass only what you need to override):

```python
Options(
    bluffing_solver_mode="research",  # "compat" mirrors the single-run legacy program
    enforce_war_payoff_s1=True,       # set False to skip the p*max1-c1<0 check
    enforce_war_payoff_s2=True,
    bluffing_sample_count=200,        # research mode: number of sample points
    denom_eps=1e-12,                  # shared near-zero denominator guard
)
```

See `CHANGELOG.md` for v1.0 delivery details and acceptance criteria.

## Planned Direction
1. Stabilize the pure computation core
2. Build the exhaustion parser and enumerator around that core
3. Add research-grade solver classification and reporting
4. Only then consider downstream tooling or visualization
## Locked Research Decisions
- Research-oriented status classification is the default reporting model.
- Bluffing solving is planned with both `compat` and `research` modes.
- Multiple roots will be preserved by the computation kernel rather than collapsed early.


