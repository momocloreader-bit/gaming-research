# Changelog

## v1.1 — 2026-04-28

### Phase 2: Loader

Table-to-kernel input bridge: reads a CSV, feeds each row to `evaluate_case`, writes a long-format result CSV.

#### Delivered modules

| File | Description |
|---|---|
| `loader/schema.py` | `KERNEL_FIELDS`, `ID_COLUMN`, `AUTO_ID_FORMAT`; `CaseRecord` and `LoaderError` frozen dataclasses |
| `loader/reader.py` | `read_cases(path)` — stdlib `csv.DictReader`; per-row `LoaderError` values; BOM-safe |
| `loader/runner.py` | Pure `run(record, options)` — forwards errors, calls `evaluate_case` for valid records |
| `loader/writer.py` | `OUTPUT_COLUMNS` tuple; `flatten()` row expansion; `write_rows()` with LF/UTF-8 |
| `loader/cli.py` + `__main__.py` | `python -m gaming_research.loader INPUT.csv -o OUTPUT.csv`; 3 flags; stderr summary; exit codes |

#### Test coverage

20 loader tests across 3 files (68 total: 48 Phase 1 + 20 loader).

| Test file | Coverage |
|---|---|
| `test_loader_reader.py` | Missing column, unparseable decimal, empty value, auto-id, case_id passthrough, empty case_id, metadata, duplicate ids, UTF-8 BOM, leading/trailing spaces |
| `test_loader_writer.py` | All 4 result statuses, 2-solution expansion, `is_selected`, `m_star=None`, float format, LF endings, metadata column order |
| `test_loader_end_to_end.py` | Byte-for-byte golden CSV comparison (4-row fixture) |

#### Acceptance criteria (all satisfied)

- [x] `docs/loader-implementation-plan.md` exists and reviewed before any code
- [x] `pytest` passes (48 + 20 loader tests = 68 total)
- [x] CLI end-to-end golden file matches byte-for-byte
- [x] No pandas/polars imports in `src/gaming_research/loader/`
- [x] No `print(`/`open(` in `schema.py`/`runner.py`
- [x] No kernel files modified in Phase 2
- [x] `pyproject.toml` deps still `["scipy"]`
- [x] `CaseRecord` and `LoaderError` are `@dataclass(frozen=True)`
- [x] No files under `exhaustion/` or `cli/`



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
