# CLAUDE.md — Router

**Project:** `gaming-research` — batch parameter-space enumerator for a game-theory kernel (Python 3, stdlib + scipy).

**MODE: IMPLEMENTATION**
**PHASE: 3**

## Mode routing

- When MODE is **PLANNING**: read `planning.md` as the active file; treat `implementation.md` as reference-only.
- When MODE is **IMPLEMENTATION**: read `implementation.md` as the active file; treat `planning.md` as inactive.

## Stable project-wide constants

**Repo top-level layout:**
- `src/gaming_research/` — all packages (`kernel/`, `loader/`, `exhaustion/`)
- `tests/` — pytest suite; fixtures under `tests/fixtures/`
- `docs/` — design and implementation plan docs (read-only during implementation)

**Dependency constraint:** `pyproject.toml` runtime deps must remain exactly `["scipy"]`; `pytest` lives in the dev extra only.

**Test runner:** `pytest` from the repo root.

## Layer files

- `implementation.md` — critical rules (stable), anti-features, when-in-doubt guidance, and all Phase 3 state (mission, architecture, coding order, acceptance criteria, post-phase docs). **Active now.**
- `planning.md` — goals, constraints, open questions, and design decisions for the *next* phase. **Inactive during implementation.**
