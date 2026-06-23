# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-23)

**Core value:** When EU4 writes an autosave, the app parses it and refreshes the UI with risk alerts + top-3 recommendations within a few seconds, with zero unhandled errors.
**Current focus:** Phase 1 — Restore the Live Watch Loop

## Current Position

Phase: 1 of 4 (Restore the Live Watch Loop)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-06-23 — Roadmap created from ingest; M1–M10 confirmed shipped, live loop confirmed broken

Progress: [░░░░░░░░░░] 0% (new milestone; M1–M10 already shipped as prior work)

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: -
- Total execution time: -

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Ingest]: 10 SPEC-level design decisions treated as binding-but-not-locked (no ADRs).
- [Ingest]: M1–M10 are Validated (shipped, 132 unit tests); the next milestone repairs the loop that ties them together.
- [Phase 4]: Canonical version string and mode terminology to be settled (0.5.0 vs "v1.0"; "Advisor" vs `assist`).

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- **HIGH (Phase 1):** Live UI pipeline calls `ClausewitzTextParser().parse(...)` at `main.py:201`; class only defines `parse_text()`/`parse_file()` — every save raises `AttributeError`. Flagship feature broken.
- **HIGH (Phase 1):** Over-broad `except (SaveFormatError, Exception)` at `main.py:203` swallows the bug (and any internal error) into one log line.
- **MED (Phase 2):** Auto-pause sends `F1` (`pause_controller.py:73`); EU4 pause is Space (`executor.py:141`) — the two disagree.
- **Wiring (Phase 2):** `PauseController` and `ui/hotkey.py` `HotkeyManager` are unit-tested but never instantiated in `run_with_ui()` — auto-pause and F2 do nothing end-to-end.
- **HIGH safety (Phase 3):** FULL_BOT executes with no confirmation; `requires_confirmation` ignored in `execute()`; no focus guard / `pyautogui.FAILSAFE`.
- **MED (Phase 4):** CI tests 3.11/3.12 but runtime interpreter is 3.14; `pynput` top-level import in `ui/hotkey.py` can break the whole UI import.
- **Coverage:** No test covers `run_with_ui`/`_process_save`/`_watcher_loop`; parser→extractor integration untested (extractor fed a hand-built dict only).

## Deferred Items

Items acknowledged and carried forward:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Automation | Real menu-navigation actions (execute() only sends pause) | v2 (AUTO-01/02) | 2026-06-23 |
| Parser | Recursion/size guards, streaming, atomic-rename handling | v2 (HARD-01/02/03) | 2026-06-23 |
| Tech debt | Remove legacy parser alias; consolidate coercion/adapters; lockfile | v2 (DEBT-01/02/03) | 2026-06-23 |

## Session Continuity

Last session: 2026-06-23 21:00
Stopped at: Wrote PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md from ingest intel + codebase map.
Resume file: None
