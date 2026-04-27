# CLAUDE.md

Briefing for the implementer of **Phase 1** of `gaming-research`.

## Current Development State
<!-- Updated 2026-04-27 -->

**v1.0 — Phase 1 complete.** The pure computation kernel is implemented, 48/48 tests pass, and the code is on `claude/working`. See `CHANGELOG.md` for the full delivery record.

**Next phase: Phase 2 — `loader/`** (spec: `docs/loader-design.md`). Before starting, write a new CLAUDE.md briefing scoped to Phase 2 and update this section.

---

## Mission
Implement the pure computation kernel exactly as specified in `docs/kernel-implementation-plan.md`. The kernel must:

- accept one parameter case in
- return one structured `KernelResult` out
- have **zero side effects**: no file I/O, no `print`, no `input()`, no `stdout` capture, no regex on text output

Phase 2 (`loader/`) and Phase 3 (`exhaustion/`) are **out of scope**. Do not start them. Do not create stub files for them.

## Read These First (in order)
1. `docs/kernel-implementation-plan.md` — primary spec, the source of truth for *how*.
2. `docs/core-kernel-design.md` — the contract; defines *what* the kernel must produce.
3. `docs/current-program-algorithm.md` — math reference for the GT formula and the bluffing residual derivation. **Do not copy its module structure or its stdout-based bluffing flow.** Use it only as a math reference.
4. `README.md` — short repo-level context.

Skip these for this phase:
- `docs/loader-design.md` — Phase 2; do not implement.
- `docs/exhaustion-design.md` — Phase 3; do not implement.
- `docs/exhaustion.txt` — constraint spec consumed by Phase 3.

## Critical Rules
Non-negotiable. These override any local-feeling tradeoff.

- **No legacy code imports.** Do not import or shell out to `main.py`, `gt.py`, `gaming1030.py`, `ui.py`, or anything resembling them. None are in this repo. Re-derive the math from `current-program-algorithm.md`.
- **No I/O in kernel.** No file writes, no `print`, no `input()`, no `sys.stdout` redirection, no regex parsing of text output.
- **Decimal at the boundary, float in math.** `Params` may carry `Decimal`; convert to `float` once at the boundary of `derived.py` and the solvers. Echo the original values unchanged in `KernelResult.params`.
- **Frozen dataclasses everywhere.** `@dataclass(frozen=True)` for every result struct. Use `tuple[...]` not `list[...]` for sequence fields. Serialization is the caller's job (`dataclasses.asdict`); the kernel does not serialize.
- **Options is locked.** Use exactly the field names, types, and defaults in `kernel-implementation-plan.md` § "Options dataclass". Do not add fields. Do not rename fields. Do not change defaults.
- **English messages only.** `failure_codes` are the stable contract; `failure_messages` are short English text.
- **Single epsilon for divisor guards.** Every "is the denominator effectively zero?" check uses `options.denom_eps`. Do not introduce other epsilons.
- **Multiple roots are preserved.** The kernel never collapses bluffing roots to one. Out-of-support roots stay in `solutions` with `in_support=False`.
- **No comments by default.** Add a one-line comment only when *why* is non-obvious. No multi-paragraph docstrings.
- **No new dependencies** beyond `scipy` and `pytest`.
- **No README edits, no new docs.** The design docs are locked. If something is genuinely ambiguous, stop and ask — do not invent.

## Coding Order
Implement in this order. Each step should leave a runnable, importable state. Use `TodoWrite` to track these and commit after each meaningful step (commit message style: `MMDD-short-slug`, see `git log`).

1. `pyproject.toml` — hatchling backend, Python 3.11+, deps `scipy`, `pytest`.
2. `src/gaming_research/__init__.py` and `src/gaming_research/kernel/__init__.py` — re-exports populated as you go.
3. `src/gaming_research/kernel/types.py` — `Params`, `Options`, `Derived`, `Validation`, `Branch`, `Solution`, `Summary`, `KernelResult`. All frozen dataclasses per the plan doc.
4. `src/gaming_research/kernel/derived.py` — `F1`, `F2`, and `compute_derived(params) -> Derived`.
5. `src/gaming_research/kernel/validation.py` — the 10 validation codes, their messages, and `validate(params, options) -> Validation`. Honor the war-payoff toggles.
6. `src/gaming_research/kernel/gt.py` — closed-form GT solver. Returns `tuple[Solution, ...]` plus a `status_detail` string.
7. `src/gaming_research/kernel/bluffing.py` — `build_residual`, `solve_compat`, `solve_research`, dispatched by `options.bluffing_solver_mode`.
8. `src/gaming_research/kernel/api.py` — `evaluate_case(params, options=None) -> KernelResult` orchestrating validation -> derive -> branch -> solve -> summarize.
9. `tests/` — five test files per the plan doc.
10. Run `pytest` from the repo root; iterate until clean.

## Acceptance Criteria
The phase is done when **all** of these are true. Verify each before declaring completion.

- [x] `pyproject.toml` exists; `pip install -e .` succeeds in a fresh venv.
- [x] `python -c "from gaming_research.kernel import evaluate_case, Options, Params"` succeeds.
- [x] `pytest` from the repo root reports all tests passing.
- [x] `grep -rE "print\(|^[^#]*input\(|open\([^)]*['\"]w" src/gaming_research/kernel/` returns no match.
- [x] No file under `src/gaming_research/kernel/` imports `gaming1030`, legacy `gt`, `main`, `ui`, or anything from outside `src/gaming_research/`.
- [x] Every result class is a `@dataclass(frozen=True)`.
- [x] `dataclasses.asdict(result)` round-trips cleanly for at least one GT case and one bluffing case in tests.
- [x] No files under `src/gaming_research/loader/`, `src/gaming_research/exhaustion/`, or `src/gaming_research/cli/`.
- [x] `Options` has exactly the fields, order, and defaults specified in the plan doc.
- [x] No new files in `docs/`. No edits to existing docs.

## Post-Phase Documentation
<!-- Added 2026-04-27 -->

When all acceptance criteria for a phase are satisfied, do the following before declaring completion:

1. **`CHANGELOG.md`** (repo root) — add a versioned entry: date, phase name, delivered modules table, test count, and the acceptance criteria checklist. Create the file if it does not yet exist.
2. **`README.md`** — add or update the integration guide section for the newly completed modules. Mark each edit with an HTML comment: `<!-- Added YYYY-MM-DD: reason -->`. Keep the guide brief: install command, minimal call example, key result fields, serialization note.

Commit both files together in a single `MMDD-vX.Y-docs` commit immediately after the implementation commit.

---

## Anti-Features (Do Not Build)
These look helpful but are explicitly off-limits this phase:

- a CLI (no `__main__.py`, no `argparse`)
- a loader, exhaustion parser, or batch runner
- compatibility wrappers for `audit.txt` / `audit_display.json`
- README updates or new design docs
- additional `Options` fields, additional validation codes, additional status details
- "convenience" facades that wrap `evaluate_case`
- backwards-compat shims (there is no legacy state in this repo)
- emoji in code, comments, or commit messages
- multi-paragraph docstrings or "what" comments

## When in Doubt
- If `kernel-implementation-plan.md` and another doc disagree: the **plan doc wins**.
- If something is genuinely missing from both the plan and the contract: stop and ask. Do not invent.
- If a test needs a "known good" parameter set that the plan doesn't pin, pick values from within the legal parameter space and record them as a short comment in the test file. This is one of the few places a comment is appropriate.
