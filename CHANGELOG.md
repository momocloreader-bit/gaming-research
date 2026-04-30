# Changelog

## v1.2 — 2026-04-30

### Phase 3: Exhaustion Enumerator

Batch parameter-space enumerator: grids all valid `(min1, min2, p, c1, c2)` combinations, runs each through the kernel via the loader, and writes a long-format result CSV plus a metadata JSON.

#### Delivered modules

| File | Description |
|---|---|
| `exhaustion/spec.py` | `GridSpec` frozen dataclass; `CURRENT_SPEC` constant encoding `docs/exhaustion.txt`; `estimate_case_count`; `reduction_eligible` |
| `exhaustion/enumerate.py` | `enumerate_cases(spec, options)` — two paths: analytical reduction (3920 cases) or full grid (~14M); Decimal arithmetic throughout; `case_id` formatter |
| `exhaustion/runner.py` | Thin `run_all(spec, options)` — iterates `enumerate_cases`, delegates to `loader.runner.run` |
| `exhaustion/writer.py` | `write_cases` (delegates to `loader.writer.flatten`/`write_rows`); `write_metadata` (sorted-key JSON, LF UTF-8) |
| `exhaustion/cli.py` + `__main__.py` | `python -m gaming_research.exhaustion -o cases.csv [...]`; safety gate (100k threshold); stderr summary; exit codes |

#### Test coverage

17 new exhaustion tests across 4 files (85 total: 48 Phase 1 + 20 Phase 2 + 17 exhaustion).

| Test file | Coverage |
|---|---|
| `test_exhaustion_spec.py` | Valid-pair count (35); estimate with reduction (3920) and full grid (14,112,000); `reduction_eligible` on/off |
| `test_exhaustion_enumerate.py` | Case count; c1/c2 window values; `case_id` format; Decimal text; full-grid start; avg_diff_min filter |
| `test_exhaustion_writer.py` | `write_cases` row count; `write_metadata` JSON keys; metadata path derivation |
| `test_exhaustion_end_to_end.py` | Byte-for-byte golden `cases.csv`; key-by-key golden `metadata.json` (TINY_SPEC, 16 cases) |

#### Acceptance criteria (all satisfied)

- [x] `docs/exhaustion-implementation-plan.md` exists and reviewed before any code
- [x] `pytest` passes (48 + 20 + 17 = 85 total)
- [x] CLI end-to-end golden `cases.csv` matches byte-for-byte (TINY_SPEC)
- [x] Safety gate fires (exit 2) without `--allow-large-grid` on full-grid path; passes on reduction path
- [x] No pandas/polars/yaml imports in `src/gaming_research/exhaustion/`
- [x] No `print(`/`open(`/`sys.stdout`/`sys.stderr` in `spec.py`, `enumerate.py`, `runner.py`
- [x] No kernel or loader files modified in Phase 3
- [x] `pyproject.toml` deps still `["scipy"]`
- [x] `GridSpec` is `@dataclass(frozen=True)`
- [x] No files under `src/gaming_research/cli/`
- [x] Reduction path yields exactly 3920 cases for `CURRENT_SPEC` with default options
- [x] Decimal text canonical: `min1 → "2"`, `p → "0.3"`, `a1 → "0.5"`, `c1 → "5.2"`, etc.

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
