# Changelog

## v1.4 — 2026-05-14

### Phase 4: `c1` / `c2` Segment-Union Axes (schema v2)

`c1` and `c2` now accept arbitrary axes built from any number of `RangeSegment` and `PointsSegment` entries. The schema bumps from v1 to v2; v1 spec files are auto-migrated in-memory at load time and a one-line `stderr` notice fires. `min1_values`, `min2_values`, `p_values` are unchanged (they were already point lists).

The reduction window keeps its v1 semantic: `p*max1 < c1 < p*max1 + a1` and `(1-p)*max2 < c2 < (1-p)*max2 + a2` — strictly open on both ends. Point lists are filtered against this window after materialization.

**v1 → v2 migration**: `c1_min` / `c1_max` / `c1_step` (and c2 equivalents) are removed as `GridSpec` fields; they survive only as keys recognized by an in-memory `_migrate_v1_to_v2` step. The dumped `metadata.json` spec block is now v2-shaped (self-describing `"schema_version": 2`, `c1` / `c2` as segment lists).

| File | Change |
|---|---|
| `exhaustion/spec.py` | + `RangeSegment`, `PointsSegment`, `AxisSegment`; `GridSpec.c1` / `c2` are segment tuples; + `from_dict_with_meta`, `_migrate_v1_to_v2`, `materialize_axis`; reduction window filter rewritten to materialized-point form |
| `exhaustion/enumerate.py` | Both `_full_grid_cases` and `_reduction_cases` rewritten to iterate materialized axes; window semantic preserved |
| `exhaustion/cli.py` | Uses `from_dict_with_meta`; emits the migration `stderr` notice when triggered; `_spec_to_dict` outputs v2 shape |
| `samples/exhaustion_spec.example.json` | Upgraded to schema v2 (single range segment, semantically equivalent) |
| `tests/fixtures/exhaustion/` | + `v1_spec.json`, `v2_spec.json`, `points_spec.json`; `tiny_spec.py` and `expected_metadata.json` upgraded to v2 shape |
| `docs/exhaustion-points-plan.md` | New — plan doc for this phase |
| `docs/exhaustion-usage.md` | + Segment Syntax section, v1 auto-migration note |

#### Test coverage

117 tests pass (10 new spec cases + 5 new enumerate cases + 1 new end-to-end case + adjustments to existing tests):

| Test file | New / changed |
|---|---|
| `test_exhaustion_spec.py` | +10 cases (v2 parse, v1 migration flag, version mismatches, mixed-field rejection, segment validation) |
| `test_exhaustion_spec_loader.py` | Rewritten to v2 dicts |
| `test_exhaustion_enumerate.py` | +5 cases (points enumeration, multi-segment dedupe/sort, reduction-window two-end-open boundary, points filtering inside window) |
| `test_exhaustion_end_to_end.py` | +1 case (`points_spec.json` end-to-end) |
| `test_exhaustion_cli_spec_file.py` | v2 happy path + v1 migration-notice path |
| `test_exhaustion_writer.py` | Fixture upgraded to v2 |

#### Acceptance criteria (all satisfied)

- [x] `pytest` passes (117 tests; 1 unrelated Phase-2 hardcoded-`python` failure is out of scope)
- [x] Every test case listed in `docs/exhaustion-points-plan.md` §测试覆盖 implemented and passes
- [x] CLI run against a v1 spec emits the migration notice on stderr exactly once
- [x] CLI run against a v2 spec emits no migration notice
- [x] `grep -rE "print\(|open\(|sys\.stdout|sys\.stderr" src/gaming_research/exhaustion/spec.py src/gaming_research/exhaustion/enumerate.py src/gaming_research/exhaustion/runner.py` returns no match
- [x] No file under `src/gaming_research/kernel/` or `src/gaming_research/loader/` modified
- [x] `pyproject.toml` runtime deps still `["scipy"]`
- [x] `GridSpec`, `RangeSegment`, `PointsSegment` are all `@dataclass(frozen=True)`
- [x] `c1_min`/`c1_max`/`c1_step` (and c2 equivalents) appear in `spec.py` only as keys for `_migrate_v1_to_v2`; not `GridSpec` fields
- [x] On `CURRENT_SPEC` with default options, reduction path still yields **3920 cases** (Phase 3 regression)

#### Field experiment

The `samples/worksheet1.csv` study set was used to cross-validate the two ingestion paths end-to-end. Loader: 72 → 72 solved. Exhaustion with a segment-union spec covering worksheet1's `c1` / `c2` axis values: 400 cases (20 × 20 Cartesian). worksheet1's 72 `(c1, c2)` keys are a strict subset of exhaustion's 400; all 16 compared kernel-output fields match across the 72 shared cases.

## v1.3 — 2026-05-07

### Customizable `GridSpec` via `--spec-file`

The exhaustion CLI now accepts `--spec-file PATH`, loading a full `GridSpec` from JSON at runtime. When the flag is omitted the built-in `CURRENT_SPEC` is used (no behavior change for existing invocations). All 14 `GridSpec` fields are configurable; values must be JSON strings to preserve `Decimal` precision. The schema is validated up-front (non-empty value lists; `span > 0`; `step > 0`; `c?_min <= c?_max`; `a1`/`a2`/`avg_diff_min >= 0`); failure exits 2 with a stderr message naming the offending field.

`metadata.json` gains a `spec_source` field — the `--spec-file` path string when supplied, `"CURRENT_SPEC"` otherwise. The `spec` block format is unchanged, so a previous run's `metadata.json` `spec` block (plus `"schema_version": 1`) round-trips back through `--spec-file`.

`a1`/`a2` ≠ `0.5` falls through to the existing full-grid path (`reduction_path: "full_grid"`); the 100,000-case safety gate continues to apply.

| File | Change |
|---|---|
| `exhaustion/spec.py` | + `GridSpec.from_dict`, `_validate_spec` (pure, no I/O) |
| `exhaustion/cli.py` | + `--spec-file` flag, `spec_source` metadata field |
| `samples/exhaustion_spec.example.json` | New copy-paste template |
| `tests/test_exhaustion_spec_loader.py` | New — parser + validator unit tests |
| `tests/test_exhaustion_cli_spec_file.py` | New — CLI integration tests |
| `docs/exhaustion-usage.md` | + "自定义参数空间" section |

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
