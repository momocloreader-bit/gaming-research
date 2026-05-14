# implementation.md

## Critical Rules
Non-negotiable. These override any local-feeling tradeoff.

- **Kernel is locked.** Do not edit anything under `src/gaming_research/kernel/`. Do not add fields to `Options`, `Params`, `KernelResult`, or any other kernel type.
- **Loader is locked.** Do not edit anything under `src/gaming_research/loader/`. The exhaustion package consumes the loader API as-is. If something is missing, stop and ask — do not "extend" the loader.
- **Stdlib only.** No pandas, no polars, no PyYAML, no toml-parser. `pyproject.toml` runtime deps stay at `["scipy"]` (and `pytest` in the dev extra).
- **In-memory pipeline only.** No intermediate parameter CSV between the enumerator and the runner. `enumerate_cases` yields `CaseRecord` objects directly into `loader.runner.run`. Output files are still exactly `cases.csv` and the matching `metadata.json`.
- **Decimal text is canonical.** Every kernel-field value the enumerator produces uses `str(Decimal_value)` after `Decimal` arithmetic. The loader's byte-for-byte passthrough must then carry that exact string into `cases.csv`.
- **Reduction is gated by an explicit predicate.** `enumerate.py` checks `options.enforce_war_payoff_s1 and options.enforce_war_payoff_s2 and spec.a1 == Decimal('0.5') and spec.a2 == Decimal('0.5')`. Only when all four hold may the reduction path apply.
- **Reduction window is open on both ends.** `p*max1 < c1 < p*max1 + a1` and `(1-p)*max2 < c2 < (1-p)*max2 + a2` — strict inequality on both sides. This is the v1 semantic; the v2 axis upgrade preserves it.
- **I/O is confined.** Only `cli.py` and `writer.py` touch the filesystem or stdio. `spec.py`, `enumerate.py`, and `runner.py` are pure: no `open`, no `print`, no `sys.stdout`, no `sys.stderr`. The v1→v2 auto-migration **stderr notice is emitted by the CLI layer**, never by `spec.py`; `spec.py` surfaces a flag the CLI consults.
- **Frozen dataclasses everywhere.** `@dataclass(frozen=True)` for `GridSpec`, `RangeSegment`, `PointsSegment`. Use `tuple[...]` for sequence fields. `AxisSegment = RangeSegment | PointsSegment`.
- **Single-threaded, single-process.** No multiprocessing, no threading, no asyncio.
- **Safety gate is mandatory.** When `estimate_case_count(spec, options)` exceeds the Phase 3 threshold (100 000), the CLI exits non-zero with a stderr message before any case runs. `--allow-large-grid` is the only override. Threshold value is unchanged in Phase 4.
- **English messages only.** Stable codes are the contract; any human-readable text is short English. The migration notice text is pinned in `docs/exhaustion-points-plan.md`.
- **No comments by default.** One-line *why* comments only. No multi-paragraph docstrings.

## Anti-Features (Do Not Build)
These look helpful but are explicitly off-limits this phase:

- spec-level multi-block / union-of-grids — out of scope; if a study is a union of disjoint grids or correlated tuples, use the loader CSV path
- axis-segment-union for `min1_values`, `min2_values`, or `p_values` — only `c1` and `c2` get the upgrade in Phase 4
- a v1/v2 dual-parsing path that keeps both shapes alive in `GridSpec` — v2 is the canonical in-memory shape; v1 is reached only through the in-memory `_migrate_v1_to_v2` step
- "two-end-closed" or "left-closed" variants of the reduction window
- a flat `c1_values` / `c2_values` shortcut alongside the segment list — a flat point list is expressed as a single `PointsSegment`
- silent v1 ingestion — the CLI must emit a one-line stderr notice when a v1 spec is auto-migrated
- new runtime dependencies, multiprocessing, resume / checkpoint, parallel execution
- any edit to `src/gaming_research/kernel/` or `src/gaming_research/loader/`, including "harmless" helpers or re-exports
- any new field on `Options`, `Params`, `KernelResult`, `CaseRecord`, or `LoaderError`
- emoji in code, comments, fixtures, or commit messages
- multi-paragraph docstrings or "what" comments

## When in Doubt
- The binding spec for this phase is `docs/exhaustion-points-plan.md`. It pins schema v2 shape, validation error strings, version-detection branches, the `_migrate_v1_to_v2` signature, fixture files, and the test list.
- If `docs/exhaustion-points-plan.md` and this `implementation.md` disagree on a **Critical Rule**, this `implementation.md` wins; stop and ask before editing the plan doc.
- If the plan doc is missing a decision (an exact error string, a fixture's contents, a CLI behavior), stop and ask. Do not invent.
- `docs/exhaustion-design.md`'s three Locked Design Decisions at the bottom still hold; the c1/c2 upgrade does not touch them.

---

<!-- PHASE STATE: replace this zone entirely when advancing to the next phase -->

## Current Development State
<!-- Updated 2026-05-14: Phase 4 complete -->

- **v1.0 — Phase 1 complete.** Pure computation kernel; 48 tests pass.
- **v1.1 — Phase 2 complete.** Loader (`src/gaming_research/loader/`); 68 tests cumulative.
- **v1.2 — Phase 3 complete.** Exhaustion enumerator with v1 schema; 85 tests cumulative. CLI: `python -m gaming_research.exhaustion -o cases.csv`. Subsequent increments (0504 default sample, 0507 `--spec-file` flag) extended the CLI without bumping the phase.
- **v1.4 — Phase 4 complete.** `c1` and `c2` axes upgraded to segment-union (any combination of range and points segments). `schema_version` bumped 1 → 2 with in-memory migration from v1. 117 tests pass. Field-experiment cross-validation via `samples/worksheet1.csv` (loader 72 → exhaustion 400 superset; 16-field kernel-output match on the 72 shared cases).

## Mission
Upgrade the `exhaustion` enumerator so `c1` and `c2` accept arbitrary segment-union axes — any number of `RangeSegment` and `PointsSegment` entries, in any order. Bump `schema_version` from 1 to 2, with transparent in-memory migration from v1 spec files. All other axes (`min1_values`, `min2_values`, `p_values`) stay unchanged.

The kernel and loader remain locked. The loader CSV path remains the right tool for studies that are truly a union of disjoint grids or correlated tuple sets.

### Scope
- Modify `src/gaming_research/exhaustion/spec.py` and `src/gaming_research/exhaustion/enumerate.py`.
- Add stderr emission for the migration notice in `src/gaming_research/exhaustion/cli.py`.
- Update `samples/exhaustion_spec.example.json` and (post-implementation) `docs/exhaustion-usage.md`.
- Add fixtures under `tests/fixtures/exhaustion/` and extend the test files listed in `docs/exhaustion-points-plan.md` §Fixtures and §测试覆盖.

## Read These First (in order)
1. `docs/exhaustion-points-plan.md` — the binding plan for this phase. Read in full before any code.
2. `src/gaming_research/exhaustion/spec.py` and `src/gaming_research/exhaustion/enumerate.py` — the two files being modified.
3. `src/gaming_research/exhaustion/cli.py` — where the stderr migration notice is emitted.
4. `tests/fixtures/exhaustion/` — existing fixtures (`tiny_spec.py`, `expected_cases.csv`, `expected_metadata.json`) that need updating to v2 form while preserving regression coverage.
5. `docs/exhaustion-design.md` — its three Locked Design Decisions at the bottom still hold.

Skip these for this phase:
- `docs/exhaustion.txt` — superseded historical reference.
- `docs/kernel-implementation-plan.md`, `docs/loader-implementation-plan.md` — finished phases.

## Coding Order
Execute in this order. Each step should leave a runnable, testable state. Commit after each step (message style: `MMDD-short-slug`, see `git log`).

1. `src/gaming_research/exhaustion/spec.py` — add `RangeSegment`, `PointsSegment`, `AxisSegment`. Change `GridSpec.c1` / `GridSpec.c2` field types. Add pure `_migrate_v1_to_v2(payload)`. Rewrite `from_dict` to do version detection → mixed-field rejection → optional migration → v2 validation, and to **return the migration flag to its caller** (e.g. `from_dict(payload) -> tuple[GridSpec, bool]`, or a sibling `from_dict_with_meta`). Update `_validate_spec`, `estimate_case_count`, `CURRENT_SPEC`.
2. `src/gaming_research/exhaustion/enumerate.py` — add `_materialize_axis(segments)` (dedupe + sort). Rewrite `_full_grid_cases` and `_reduction_cases` to iterate materialized point lists. Preserve the two-end-open reduction window.
3. `src/gaming_research/exhaustion/cli.py` — call the new spec API, and when the migration flag is set emit `note: detected schema_version=1 spec, auto-migrated to v2 in-memory` exactly once to stderr before any case runs.
4. `samples/exhaustion_spec.example.json` — convert to v2 form (single range segment, semantically equivalent to the current example).
5. `tests/fixtures/exhaustion/` — add `v1_spec.json`, `v2_spec.json`, `points_spec.json` per the plan doc. Upgrade `tiny_spec.py::TINY_SPEC` to v2 form; refresh `expected_cases.csv` and `expected_metadata.json` only if their byte content actually changes.
6. `tests/test_exhaustion_spec.py` — extend per the plan doc's 10-case list.
7. `tests/test_exhaustion_enumerate.py` — extend per the plan doc's 5-case list.
8. `tests/test_exhaustion_end_to_end.py` — add the `points_spec.json` end-to-end case.
9. `pytest` from the repo root; iterate until clean. Manually run the CLI with the existing v1 `exhaustion_spec.0514.json` to confirm the stderr migration notice fires exactly once, then with a v2 spec to confirm no notice.

## Acceptance Criteria
The phase is done when **all** of these are true.

- [ ] `pytest` from the repo root reports all tests passing.
- [ ] Every test case listed in `docs/exhaustion-points-plan.md` §测试覆盖 is implemented and passes.
- [ ] CLI run against `exhaustion_spec.0514.json` (v1) succeeds and emits the migration notice on stderr exactly once.
- [ ] CLI run against a v2 spec succeeds with no migration notice.
- [ ] `grep -rE "print\(|open\(|sys\.stdout|sys\.stderr" src/gaming_research/exhaustion/spec.py src/gaming_research/exhaustion/enumerate.py src/gaming_research/exhaustion/runner.py` returns no match.
- [ ] No file under `src/gaming_research/kernel/` or `src/gaming_research/loader/` is modified (`git diff main -- src/gaming_research/kernel/ src/gaming_research/loader/` is empty).
- [ ] `pyproject.toml` runtime deps are still exactly `["scipy"]`.
- [ ] `GridSpec`, `RangeSegment`, `PointsSegment` are all `@dataclass(frozen=True)`.
- [ ] `c1_min` / `c1_max` / `c1_step` (and c2 equivalents) appear in `spec.py` only as keys recognized by `_migrate_v1_to_v2`; they are not `GridSpec` fields.
- [ ] On `CURRENT_SPEC` with default options, the reduction path still yields the historical case count from Phase 3 (regression).

## Post-Phase Documentation
When all acceptance criteria are met:

1. **`CHANGELOG.md`** — add a `v1.3 — YYYY-MM-DD` entry: phase name (c1/c2 segment-union), schema version bump (1 → 2), in-memory migration behavior, test count delta.
2. **`docs/exhaustion-usage.md`** — add a "Segment Syntax" section with examples (single range, single points, range ∪ points, multi-range), and a brief "v1 → v2 Migration" note pointing to the auto-migration behavior.
3. **`README.md`** — short Exhaustion section update if needed (only if user-facing CLI behavior changed beyond the stderr notice).
4. Update the **Current Development State** section at the top of this `CLAUDE.md` to mark Phase 4 complete.

Commit the doc updates together in a single `MMDD-v1.4-docs` commit immediately after the implementation commit.
