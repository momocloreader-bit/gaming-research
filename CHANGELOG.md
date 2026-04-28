# Changelog

## v1.1 — in progress (2026-04-28)

### Phase 2: Loader (planning complete, implementation pending)

Design reviewed and implementation plan signed off. Code not yet written.

#### Planning deliverables

| File | Description |
|---|---|
| `CLAUDE.md` | Rewritten as Phase 2 implementer briefing; 20 locked decisions, acceptance criteria, coding order |
| `docs/loader-implementation-plan.md` | Concrete *how*: function signatures, column order, formatting rules, CLI flags, 4-row fixture parameter sets |

#### Key decisions locked

- Output: long format, LF, UTF-8, fixed column order (`case_id … p`), `is_selected` beside `root_index`
- Failures: `LoaderError` values (3 `reason_code`s); per-row, never abort batch
- Decimal text round-trips byte-for-byte through the 9 kernel-field columns
- Computed floats: `{:.10g}`; bools: `true`/`false`; `None` → `""`
- CLI: `--bluffing-mode`, `--enforce-war-payoff-s1/s2`; default `research`; exit 2 only on unreadable input
- End-to-end fixture: 4 rows (GT-valid, bluffing-single-root, validation_failed, loader_rejected); multi-root expansion covered by writer unit test with hand-crafted `KernelResult`

#### Acceptance criteria status

- [x] `docs/loader-implementation-plan.md` exists and reviewed before any code
- [ ] `pytest` passes (48 + new loader tests)
- [ ] CLI end-to-end golden file matches byte-for-byte
- [ ] No pandas/polars imports in `src/gaming_research/loader/`
- [ ] No `print(`/`open(` in `schema.py`/`runner.py`
- [ ] `git diff main -- src/gaming_research/kernel/` is empty
- [ ] `pyproject.toml` deps still `["scipy"]`
- [ ] `CaseRecord` and `LoaderError` are `@dataclass(frozen=True)`
- [ ] No files under `exhaustion/` or `cli/`



## v1.0 — 2026-04-27

### Phase 1: Pure Computation Kernel

First complete implementation of the `gaming_research.kernel` package.

#### Delivered modules

| File | Description |
|---|---|
| `kernel/types.py` | All frozen dataclasses: `Params`, `Options`, `Derived`, `Validation`, `Branch`, `Solution`, `Summary`, `KernelResult` |
| `kernel/derived.py` | Uniform CDF helpers `F1`/`F2` and `compute_derived` |
| `kernel/validation.py` | 10 validation rules with stable codes; war-payoff toggles |
| `kernel/gt.py` | Closed-form GT solver |
| `kernel/bluffing.py` | Residual factory + `compat` (fsolve) and `research` (brentq sampling) solvers |
| `kernel/api.py` | `evaluate_case` orchestration entry point |

#### Test coverage

48 tests across 5 files — all passing.

| Test file | Coverage |
|---|---|
| `test_validation.py` | Each failure code in isolation; war-payoff toggles; Decimal inputs |
| `test_gt.py` | Closed-form values; out-of-support; invalid denominator |
| `test_bluffing_compat.py` | Single convergence; `m_star` / support flags; numerical failure |
| `test_bluffing_research.py` | Multi-root; zero-root; deduplication; ascending order; `m_star` |
| `test_evaluate_case.py` | End-to-end both branches; `asdict` round-trip; all six result sections |

#### Acceptance criteria (all satisfied)

- [x] `pyproject.toml` exists; `pip install -e .` succeeds
- [x] `from gaming_research.kernel import evaluate_case, Options, Params` succeeds
- [x] `pytest` reports 48/48 passing
- [x] No `print(` / `input(` / `open(..., "w"` in `src/gaming_research/kernel/`
- [x] No legacy imports (`gaming1030`, `gt`, `main`, `ui`)
- [x] Every result class is `@dataclass(frozen=True)`
- [x] `dataclasses.asdict(result)` round-trips cleanly for GT and bluffing cases
- [x] No files under `loader/`, `exhaustion/`, or `cli/`
- [x] `Options` has exactly the fields, order, and defaults specified in the plan doc
- [x] No new files in `docs/`; no edits to existing docs

#### Out of scope (deferred to later phases)

- Phase 2: `loader/` — exhaustion table parser
- Phase 3: `exhaustion/` — batch enumerator and results artifacts
- CLI, visualization, compatibility wrappers
