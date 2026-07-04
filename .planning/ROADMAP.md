# Roadmap: EU4 Assistant + Bot

## Overview

Milestones M1–M10 are built and unit-tested (181 tests after PR #15/#17), but the codebase map
(2026-06-23) found the flagship loop is broken: the live watch pipeline calls a
parser method that does not exist, an over-broad `except` hides it, auto-pause and
the F2 hotkey are implemented yet never wired in, and the bot's safety gate is not
enforced where it matters. This milestone — **"Make the live loop real"** — turns
what was built into something that actually works together: first restore the
watch → parse → snapshot → UI loop (the core value), then wire auto-pause and the
global hotkey, then enforce the bot-safety confirmation contract before any real
keystroke, and finally reconcile the Python/CI/version drift so the project is
honestly buildable and labelled.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Restore the Live Watch Loop** - Fix the parse bug, tighten error handling, and prove the watch→snapshot→UI loop with integration tests
- [x] **Phase 2: Wire Auto-Pause & Global Hotkey** - Connect `PauseController` (correct pause key) and `HotkeyManager` (F2) into the running app
- [x] **Phase 3: Enforce the Bot-Safety Gate** - Make `execute()` honour the confirmation contract, gate FULL_BOT, add focus guard + failsafe
- [x] **Phase 4: Reconcile Version & CI Drift** - Align the tested interpreter, canonical version string, and mode terminology

## Phase Details

### Phase 1: Restore the Live Watch Loop
**Goal**: When EU4 writes an autosave, the running app parses it and refreshes the Dashboard, Advisor, and Log — the core value, currently broken.
**Depends on**: Nothing (first phase; unblocks everything else)
**Requirements**: LIVE-01, LIVE-02, LIVE-03, LIVE-04
**Success Criteria** (what must be TRUE):
  1. Running `eu4-assistant --watch <save>.eu4` and triggering a save updates the three UI columns with real snapshot data (no `AttributeError`, no generic "Errore parsing save")
  2. A malformed/corrupt save produces a clear "bad save" log entry and is skipped; an unexpected internal error is surfaced distinctly (traceback / internal-error level), not swallowed
  3. An integration test drives `_process_save` end-to-end from a real `.eu4` fixture (ZIP and plain) and asserts a populated snapshot reaches the UI
  4. A test feeds actual `ClausewitzTextParser` output into `StateExtractor` and confirms a non-empty snapshot (no silent list-vs-dict empties)
**Plans**: TBD
**UI hint**: yes

### Phase 2: Wire Auto-Pause & Global Hotkey
**Goal**: Auto-pause and the F2 show/hide window actually work during a real session.
**Depends on**: Phase 1 (auto-pause reacts to snapshots that must first flow through the live loop)
**Requirements**: PAUSE-01, PAUSE-02, HOTKEY-01, HOTKEY-02
**Success Criteria** (what must be TRUE):
  1. On an imminent-rebellion / war-declared snapshot, the running app pauses EU4 with the correct key (Space) and logs the event; `PauseController` and `ActionExecutor` use the same pause key
  2. `PauseController` is instantiated in the live UI run and is cleanly stopped on shutdown
  3. Pressing F2 globally shows/hides the companion window during a real session, and the listener is stopped on shutdown
  4. Importing the UI succeeds even when the global-hotkey backend is unavailable (degrades to "no global hotkey", does not break UI import)
**Plans**: TBD
**UI hint**: yes

### Phase 3: Enforce the Bot-Safety Gate
**Goal**: No real keystroke reaches the game without the safety contract being honoured.
**Depends on**: Phase 1 (executor is driven from the live loop); independent of Phase 2
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04
**Success Criteria** (what must be TRUE):
  1. `ActionExecutor.execute()` refuses to run a `requires_confirmation=True` plan without explicit confirmation, regardless of caller (UI or not)
  2. FULL_BOT cannot execute a confirmation-required action without an explicit, persisted user acknowledgement; the SEMI/FULL distinction is enforced in the executor
  3. Before any keystroke, the app verifies the EU4 window is focused and `pyautogui.FAILSAFE` is enabled; a misfire cannot type into another application
  4. Tests assert the exact key sent and that confirmation-required plans are blocked without confirmation, covering both the SEMI_BOT dialog path and the FULL_BOT path
**Plans**: TBD

### Phase 4: Reconcile Version & CI Drift
**Goal**: The project is honestly buildable on the interpreter it runs on, with one version string and one mode vocabulary.
**Depends on**: Phase 1 (so green CI reflects the now-working live loop)
**Requirements**: BUILD-01, BUILD-02, BUILD-03
**Success Criteria** (what must be TRUE):
  1. CI tests the interpreter the project actually runs on (3.13/3.14 added, or `requires-python` constrained to the tested range), and `pyproject.toml` classifiers match
  2. A single canonical version string appears consistently across `__init__.py`, CHANGELOG, and the design label (no 0.5.0-vs-"v1.0" ambiguity)
  3. Operating-mode terminology is reconciled to one documented mapping (display label vs CLI/enum token), so UI, CLI, and docs agree
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Restore the Live Watch Loop | 1/1 | Done (PR #15) | 2026-06-24 |
| 2. Wire Auto-Pause & Global Hotkey | 1/1 | Done (PR #15) | 2026-06-24 |
| 3. Enforce the Bot-Safety Gate | 1/1 | Done (PR #15) | 2026-06-24 |
| 4. Reconcile Version & CI Drift | 1/1 | Done (PR #15) | 2026-06-24 |

## Post-Milestone

PR #16 (cleanup, dead-code removal) + **PR #17 full-bot control surface + colonial province ranking**, mergiata 2026-06-27 (merge `2251a47`), oltre le 4 fasi della milestone. 181 test verdi.
