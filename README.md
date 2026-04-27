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

## Non-Goals For This Repository Setup Phase
- No UI code
- No packaging scripts
- No runtime coupling to `audit.txt` / `audit_display.json`

## Planned Direction
1. Stabilize the pure computation core
2. Build the exhaustion parser and enumerator around that core
3. Add research-grade solver classification and reporting
4. Only then consider downstream tooling or visualization
## Locked Research Decisions
- Research-oriented status classification is the default reporting model.
- Bluffing solving is planned with both `compat` and `research` modes.
- Multiple roots will be preserved by the computation kernel rather than collapsed early.


