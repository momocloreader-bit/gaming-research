# CLAUDE.md

Briefing for the implementer of **Phase 3** of `gaming-research`.

## Current Development State
<!-- Updated 2026-04-28: Phase 2 (v1.1) complete -->

**v1.0 — Phase 1 complete.** The pure computation kernel is implemented, 48/48 tests pass. See `CHANGELOG.md` for the full delivery record.

**v1.1 — Phase 2 complete.** The loader (`src/gaming_research/loader/`) is fully implemented: `schema.py`, `reader.py`, `runner.py`, `writer.py`, `cli.py`. All 68 tests pass (48 kernel + 20 loader). The CLI is runnable as `python -m gaming_research.loader INPUT.csv -o OUTPUT.csv`. See `CHANGELOG.md` v1.1 for the full delivery record and `docs/loader-design.md` / `docs/loader-implementation-plan.md` for the spec.

**v1.2 — Phase 3 not yet started.** The exhaustion enumerator (`src/gaming_research/exhaustion/`) is next. Spec: `docs/exhaustion-design.md` and `docs/exhaustion.txt`. The kernel and loader are locked; do not modify them.

---

## Mission
Build the **table → kernel** input bridge exactly as specified in `docs/loader-design.md` and the upcoming `docs/loader-implementation-plan.md`. The loader must:

- read a CSV via stdlib `csv.DictReader`, never pandas
- yield `CaseRecord | LoaderError` values per row — per-row failures are values, never raised exceptions
- feed each `CaseRecord.params` to `evaluate_case` from the existing kernel — no kernel edits
- write one CSV in long format: one output row per `Solution`; one row for `validation_failed`, `solver_no_valid_solution`, or `loader_rejected` cases
- preserve the original `Decimal` text of kernel parameters from input CSV string straight through to output CSV string

The kernel is locked; `exhaustion/` is out of scope. Do not start either.

## Read These First (in order)
1. `docs/loader-design.md` — primary spec, the source of truth for *what*. All "Locked Decisions" are non-negotiable.
2. `docs/loader-implementation-plan.md` — concrete *how* (function signatures, exact column order, formatting rules, fixture parameter sets). Written and reviewed *before* code; if it disagrees with `loader-design.md`, the design doc wins and you stop and ask.
3. `src/gaming_research/kernel/types.py`, `src/gaming_research/kernel/api.py` — the kernel surface you are calling. Read but do not modify.
4. `docs/kernel-implementation-plan.md` — for the Phase 1 conventions you should mirror (frozen dataclasses, `tuple[...]` not `list[...]`, English-only messages, no comments by default).

Skip these for this phase:
- `docs/exhaustion-design.md` and `docs/exhaustion.txt` — Phase 3.
- `docs/current-program-algorithm.md` — math reference, not relevant to the loader.

## Critical Rules
Non-negotiable. These override any local-feeling tradeoff.

- **Kernel is locked.** Do not edit anything under `src/gaming_research/kernel/`. Do not add fields to `Options`, `Params`, `KernelResult`, or any other kernel type. If the loader needs a value, derive it from the existing kernel output.
- **Stdlib `csv` only.** No pandas, no polars, no openpyxl. Phase 2 adds zero new runtime dependencies. `pyproject.toml` deps stay at `["scipy"]` (and `pytest` in the dev extra).
- **Per-row failures are values, not exceptions.** The reader yields `CaseRecord | LoaderError`. The runner forwards the union. The CLI never lets one bad row abort the batch.
- **Decimal text round-trips byte-for-byte.** The 9 kernel-field columns in the output equal the input strings character-for-character (trailing zeros, leading sign, scientific notation — all preserved). Computed `float` quantities use the format pinned in the plan doc. Numeric values are not re-formatted via `Decimal` arithmetic on the way out.
- **I/O is confined.** Only `reader.py`, `writer.py`, and `cli.py` touch the filesystem or stdio. `schema.py` and `runner.py` must be pure: no `open`, no `print`, no `sys.stdout`. The CLI is the only place `print` / stderr writes are allowed.
- **Frozen dataclasses everywhere.** `@dataclass(frozen=True)` for `CaseRecord` and `LoaderError`. Use `tuple[...]` for sequence fields and `Mapping[str, str]` for metadata.
- **Loader does not duplicate kernel validation.** The loader checks: required column present, value non-empty, value parseable as `Decimal`. It does not check `p ∈ (0, 1)`, `c1 > a1`, etc. Those remain the kernel's job and surface as `status = validation_failed`.
- **Output column order is fixed and exhaustive.** The exact column list lives in `loader-implementation-plan.md` and is repeated in `writer.py` as a single tuple constant. Do not reorder, rename, or omit.
- **Empty cells are the empty string.** Never `NaN`, never `None`, never `null`. `m_star=None` writes as `""`.
- **One output file.** No `results/runs/<timestamp>/` directories. The user supplies one path via `-o`.
- **CLI flags are minimal.** Phase 2 ships exactly the flags listed in `loader-design.md` § "CLI" (and pinned in the plan doc). Do not add `--xtol`, `--enforce-war-payoff-*`, or any other Options pass-through unless `loader-implementation-plan.md` explicitly lists it.
- **English messages only.** `LoaderError.reason_code` is the stable contract; `reason_detail` is short English.
- **No comments by default.** One-line *why* comments only. No multi-paragraph docstrings.
- **No new docs.** The only doc added in this phase is `loader-implementation-plan.md` itself, written in step 1 below before any code. No edits to other existing docs.
- **README only gets the post-phase integration-guide edit.** No prose updates while implementing.

## Coding Order
Implement in this order. Each step should leave a runnable, importable state. Use `TodoWrite` to track these and commit after each meaningful step (commit message style: `MMDD-short-slug`, see `git log`).

1. `docs/loader-implementation-plan.md` — write the *how* doc first, before any Python code in this phase. The user reviews and signs off before implementation begins.
2. `src/gaming_research/loader/__init__.py` and `src/gaming_research/loader/schema.py` — column constants, auto-id format, `CaseRecord`, `LoaderError`. No I/O.
3. `src/gaming_research/loader/reader.py` — `read_cases(path) -> Iterator[CaseRecord | LoaderError]`. Stdlib `csv.DictReader`. Auto-id generation. Metadata extraction.
4. `src/gaming_research/loader/runner.py` — pure: forwards `LoaderError` unchanged; calls `evaluate_case` for `CaseRecord`. Exact signature pinned in plan doc.
5. `src/gaming_research/loader/writer.py` — flatten a (case-or-error, kernel-result-or-none) pair into output row dicts; write rows in fixed column order. Owns the column-order tuple.
6. `src/gaming_research/loader/cli.py` — `python -m gaming_research.loader INPUT.csv -o OUTPUT.csv [...]`. Single argparse, single loop, stderr summary, exit code per the plan doc.
7. `tests/test_loader_reader.py`, `tests/test_loader_writer.py`, `tests/test_loader_end_to_end.py` — fixtures live under `tests/fixtures/loader/`. The end-to-end test compares output byte-for-byte against a checked-in golden CSV.
8. Run `pytest` from the repo root; iterate until clean. Then run the CLI manually on the end-to-end input fixture and confirm stderr summary and exit code match the plan doc.

## Acceptance Criteria
The phase is done when **all** of these are true. Verify each before declaring completion.

- [ ] `docs/loader-implementation-plan.md` exists and the user has signed off before implementation began.
- [ ] `pytest` from the repo root reports all tests passing (Phase 1's 48 plus the new loader tests).
- [ ] `python -m gaming_research.loader tests/fixtures/loader/input.csv -o /tmp/out.csv` exits `0` and produces a file byte-equal to the golden output fixture.
- [ ] `grep -rE "import pandas|from pandas|import polars|from polars" src/gaming_research/loader/` returns no match.
- [ ] `grep -rE "print\(|open\(" src/gaming_research/loader/schema.py src/gaming_research/loader/runner.py` returns no match.
- [ ] No file under `src/gaming_research/kernel/` has been modified (`git diff main -- src/gaming_research/kernel/` is empty).
- [ ] `pyproject.toml` runtime deps are still exactly `["scipy"]`.
- [ ] `CaseRecord` and `LoaderError` are `@dataclass(frozen=True)`.
- [ ] No files under `src/gaming_research/exhaustion/` or `src/gaming_research/cli/`.
- [ ] No edits to existing docs other than `README.md` (post-phase integration guide) and the new `loader-implementation-plan.md`.
- [ ] The 9 kernel-field columns in the golden output CSV equal the input CSV strings character-for-character.

## Post-Phase Documentation
When all acceptance criteria for Phase 2 are satisfied, do the following before declaring completion:

1. **`CHANGELOG.md`** — add a `v1.1 — YYYY-MM-DD` entry: phase name, delivered modules table, test count, acceptance checklist.
2. **`README.md`** — add a "Loader Integration Guide" section: install command, minimal CLI invocation, output column summary, link to design doc. Mark the edit with `<!-- Added YYYY-MM-DD: Phase 2 (v1.1) complete -->`.
3. Update the **Current Development State** section at the top of this `CLAUDE.md` to mark Phase 2 complete and brief the Phase 3 implementer.

Commit the three doc updates together in a single `MMDD-v1.1-docs` commit immediately after the implementation commit.

---

## Anti-Features (Do Not Build)
These look helpful but are explicitly off-limits this phase:

- pandas, polars, or any DataFrame-backed reader / writer
- Parquet / Excel / SQL / streaming / stdin input modes
- a `--config` flag, YAML/JSON schema config, or column auto-detection
- per-row option overrides via input columns (e.g. a `bluffing_mode` column)
- parallel execution, multiprocessing, async, or chunked processing
- resume / checkpoint / partial-output recovery
- run-id directory trees, timestamped output paths, summary `.md` reports
- a wide-format output mode
- compatibility wrappers for `audit.txt` / `audit_display.json`
- any new field on `Options`, `Params`, `KernelResult`, `Solution`, `Summary`, `Branch`, `Validation`, or `Derived`
- a "convenience" `evaluate_csv(...)` facade in the kernel package
- emoji in code, comments, fixtures, or commit messages
- multi-paragraph docstrings or "what" comments

## When in Doubt
- If `loader-design.md` and `loader-implementation-plan.md` disagree: the **design doc wins**. Stop and ask before implementing the disagreeing piece.
- If something is genuinely missing from both docs: stop and ask. Do not invent. The output column order, the formatting of any specific value, the stderr text, and the exit code semantics are all things that must be pinned in the plan doc — if you cannot find them there, the plan doc is incomplete.
- If a test needs a "known good" parameter set that the plan doc's fixture section does not pin, stop and ask. End-to-end golden files cannot be authored ad-hoc; they go in the plan doc and get reviewed.
