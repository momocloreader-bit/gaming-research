# gaming-research

This repository is dedicated to the research-side core algorithm work that is being split out from the UI-oriented `gaming` repository.

## Requirements

- **Python 3.11+**
- **scipy >= 1.9** (only runtime dependency; installed automatically via `pip install -e .`)
- pytest >= 7 (dev only, for running the test suite)

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

## Loader Integration Guide
<!-- Added 2026-04-28: Phase 2 (v1.1) complete -->

The loader reads a parameter CSV, runs each row through the kernel, and writes a long-format result CSV.

Install (same package, no extra deps):

```bash
pip install -e .
```

Minimal invocation:

```bash
python -m gaming_research.loader INPUT.csv -o OUTPUT.csv
```

Optional flags:

```bash
python -m gaming_research.loader INPUT.csv -o OUTPUT.csv \
    --bluffing-mode compat \
    --enforce-war-payoff-s1 false \
    --enforce-war-payoff-s2 false
```

Input CSV must have columns: `min1 max1 min2 max2 a1 a2 c1 c2 p`. A `case_id` column is optional (auto-generated as `row_00001`, ... if absent). All other columns are forwarded as passthrough metadata.

Output column summary (long format — one row per `Solution`):

| Column group | Columns |
|---|---|
| Identity | `case_id`, metadata columns (input order) |
| Status | `status`, `status_detail`, `scenario`, `solver_mode` |
| Solution | `root_index`, `is_selected`, `v1_hat`, `v2_hat`, `in_support`, `F1_v1_hat`, `F2_v2_hat`, `m_star` |
| Derived | `v1_star`, `v2_star`, `F1_v1_star`, `F2_v2_star`, `GT_rhs`, `GT_condition` |
| Loader error | `loader_error_code`, `loader_error_detail` |
| Parameters | `min1 max1 min2 max2 a1 a2 c1 c2 p` (exact input strings) |

`status` values: `solver_has_valid_solution`, `solver_no_valid_solution`, `validation_failed`, `loader_rejected`. All four appear as output rows; per-row failures never abort the batch. Exit code is `0` on normal completion, `2` on unreadable input/output or invalid CLI arguments.

See `docs/loader-design.md` for full specification and `docs/loader-implementation-plan.md` for implementation details.

## Exhaustion Integration Guide
<!-- Added 2026-04-30: Phase 3 (v1.2) complete -->

The exhaustion package enumerates all valid parameter combinations from `docs/exhaustion.txt`, runs each through the kernel, and writes a long-format result CSV plus a metadata JSON.

Install (same package, no extra deps):

```bash
pip install -e .
```

Minimal invocation:

```bash
python -m gaming_research.exhaustion -o cases.csv
```

Optional flags:

```bash
python -m gaming_research.exhaustion -o cases.csv \
    --bluffing-mode compat \
    --enforce-war-payoff-s1 false \
    --enforce-war-payoff-s2 false \
    --allow-large-grid
```

**Output files** (derived from `-o`):

| File | Contents |
|---|---|
| `cases.csv` | Long-format results — same column set as the loader output; one row per `Solution` |
| `cases.metadata.json` | Spec snapshot, options, case count, runtime, reduction path flag |

**Safety gate**: by default the CLI refuses to run if the estimated case count exceeds 100,000. Pass `--allow-large-grid` to bypass. With default options (both war-payoff checks enforced, `a1=a2=0.5`) the analytical reduction path yields **3920 cases**; without it the full grid yields ~14M cases.

**Reduction path**: when both `--enforce-war-payoff-s1` and `--enforce-war-payoff-s2` are `true` and `a1=a2=0.5`, the enumerator applies analytical domain reduction — `c1` and `c2` are narrowed to 4 candidates each per `(min1, min2, p)` triple. The `metadata.json` field `reduction_path` records which path was taken (`"analytical_reduction"` or `"full_grid"`).

See `docs/exhaustion-design.md` for full specification and `docs/exhaustion-implementation-plan.md` for implementation details.

## 分支管理约定（人工备查，AI 不必遵守）
<!-- 记录于 2026-04-28，供项目维护者参考 -->

本项目的分支结构：

| 分支 | 用途 |
|---|---|
| `main` | 稳定版本，每个 phase 验证完成后从 `claude/working` 合并进来 |
| `claude/working` | 验证中间层；各 phase 的功能分支先合进这里，跑完验收后再合 `main` |
| `claude/<task>-<slug>` | AI 执行具体任务时使用的临时分支，完成即可删除 |

**合并节点**：一个 phase 的所有代码写完、`pytest` 全绿、CLI 端到端验证通过后，从 `claude/working` 向 `main` 开 PR。PR description 引用 `CHANGELOG.md` 里对应版本的验收清单，逐条确认。

**临时分支清理**：功能/计划分支的提交 fast-forward 进 `claude/working` 之后即可删除，无需保留：

```bash
git branch -d claude/<task>-<slug>
git push origin --delete claude/<task>-<slug>
```

如需保留某个实验性分支的历史起点但不想留分支，打轻量 tag 代替：

```bash
git tag archive/<task>-<slug>
git branch -d claude/<task>-<slug>
```

## Planned Direction
1. Stabilize the pure computation core
2. Build the exhaustion parser and enumerator around that core
3. Add research-grade solver classification and reporting
4. Only then consider downstream tooling or visualization
## Locked Research Decisions
- Research-oriented status classification is the default reporting model.
- Bluffing solving is planned with both `compat` and `research` modes.
- Multiple roots will be preserved by the computation kernel rather than collapsed early.


