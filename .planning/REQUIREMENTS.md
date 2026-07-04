# Requirements: EU4 Assistant + Bot

**Defined:** 2026-06-23  
**Updated:** 2026-06-27 — milestone "Make the live loop real" completa (PR #15, tutte le 15 v1 req shipped); post-milestone PR #17 mergiata (181 test).
**Core Value:** When EU4 writes an autosave, the app parses it and refreshes the UI with risk alerts and top-3 recommendations within a few seconds, with zero unhandled errors.

This project already shipped milestones M1–M10 (132 unit tests). The codebase map
(2026-06-23) found the flagship live-watch loop is broken end-to-end and several
safety/wiring gaps remain. The **v1 requirements below define the next milestone**
("Make the live loop real"): the work needed to make what was built actually work
together. **All 15 v1 requirements are now Done (PR #15, 2026-06-24; 181 tests).**
Already-shipped capabilities are listed under "Shipped" for reference and
are not re-planned unless a v1 requirement repairs them.

## v1 Requirements

The active milestone. Each maps to exactly one roadmap phase.

### Live Pipeline

- [x] **LIVE-01**: When EU4 writes an autosave, the watch pipeline parses it into a `GameSnapshot` and refreshes the Dashboard, Advisor, and Log (no `AttributeError`; `main.py` calls `parse_text`, not `parse`)
- [x] **LIVE-02**: A genuinely malformed/corrupt save produces a clear "bad save" log entry and is skipped, while an unexpected internal error (programming bug) is surfaced distinctly (logged with traceback / internal-error level), not collapsed into the generic "Errore parsing save" message
- [x] **LIVE-03**: An automated integration test drives `_process_save` end-to-end from a real `.eu4` fixture (ZIP and plain) through `SaveUnzipper → ClausewitzTextParser → StateExtractor`, so the live path cannot regress with a green suite
- [x] **LIVE-04**: Parser→extractor integration is tested against actual parser output (not a hand-built dict), so a shape mismatch (e.g. list vs dict `countries`) cannot silently produce an empty snapshot

### Auto-Pause & Hotkey Wiring

- [x] **PAUSE-01**: On a critical event (imminent rebellion / war declared) the running app actually pauses EU4 using the correct key (Space), and the event is logged; `PauseController` and `ActionExecutor` agree on one pause key
- [x] **PAUSE-02**: `PauseController` is instantiated and wired into the live UI run so auto-pause fires during a real session, and is cleanly stopped on shutdown
- [x] **HOTKEY-01**: Pressing F2 (configurable) globally shows/hides the companion window during a real session; `HotkeyManager` is wired into the live UI run and stopped on shutdown
- [x] **HOTKEY-02**: Importing the UI does not fail when the global-hotkey backend is unavailable — the app degrades to "no global hotkey" instead of breaking the whole UI import

### Bot Safety Gate

- [x] **SAFE-01**: `ActionExecutor.execute()` enforces the confirmation contract itself — a plan with `requires_confirmation=True` is never executed without explicit confirmation, regardless of caller (UI or not)
- [x] **SAFE-02**: FULL_BOT does not execute a confirmation-required action without an explicit, persisted user opt-in/acknowledgement; the SEMI_BOT/FULL_BOT distinction is enforced at the executor, not only the UI
- [x] **SAFE-03**: Before sending any keystroke to the game, the app verifies the EU4 window is focused and a failsafe is enabled (`pyautogui.FAILSAFE`), so a misfire cannot type into another application
- [x] **SAFE-04**: The bot-safety behaviour is covered by tests asserting the exact key sent and that confirmation-required plans are blocked without confirmation (SEMI_BOT dialog path and FULL_BOT path both exercised)

### Build & Version Hygiene

- [x] **BUILD-01**: The CI matrix tests the interpreter the project actually runs on (add 3.13/3.14 or constrain `requires-python` to the tested range), and `pyproject.toml` classifiers match
- [x] **BUILD-02**: A single canonical version string is chosen and applied consistently (`__init__.py`, CHANGELOG, design label), removing the 0.5.0-vs-"v1.0" ambiguity
- [x] **BUILD-03**: Operating-mode terminology is reconciled to one canonical mapping (display label vs CLI/enum token) and documented, so UI, CLI, and docs no longer drift

## v2 Requirements

Deferred to a future milestone. Tracked, not in the current roadmap.

### Real Action Automation

- **AUTO-01** *(in progress — colonist slice)*: `ActionExecutor.execute()` performs real in-game menu navigation for at least one action category. **Done for `colonial_send_colonist`**: screen capture → cv2 template match on the English base UI → click the nearest colonizable marker in view → click the Colonize button, via `navigation.Navigator`. Other categories still pause only. Targeting is "nearest in view"; `rank_colonizable` is advisory.
- **AUTO-02** *(in progress — colonist slice)*: Each real action does pre-check (template match) → execute → post-check → fallback+log on mismatch, with success inferred from observed game state, not "did press() raise". **Done for colonize**: pre-check (marker visible, then Colonize button present in panel) → click → post-check (Colonize button consumed once colonization starts) → fallback statuses `precheck_failed` / `postcheck_mismatch` / `executed_no_nav`. The orchestration is covered headless (DI `Navigator`); the live cv2/click path is verified manually on Windows + EU4. Full-bot safety hardening (kill-switch + persisted opt-in) is tracked separately.

### Parser Hardening

- **HARD-01**: Recursion-depth and max-size guards on the Clausewitz parser; large-file / deeply-nested / truncated / adversarial fixtures
- **HARD-02**: Streaming or player-block-only parse so a tens-of-MB save does not fully materialise on the watcher thread each month
- **HARD-03**: Watcher handles the EU4 temp-then-rename save pattern (`on_moved`) and joins/cancels the debounce timer on shutdown

### Tech-Debt Cleanup

- **DEBT-01**: Remove the deprecated `ClausewitzParser`/`_LegacyClausewitzParser` alias after a deprecation window
- **DEBT-02**: Consolidate the three coercion implementations and two snapshot-input formats into shared modules; deprecate the `--snapshot-save` key=value path
- **DEBT-03**: Add a dependency lockfile and review the upper-bound pins (and the lone uncapped `pytest`)

## Shipped (M1–M10)

Already implemented and unit-tested (181 tests after PR #15/#17). Listed for traceability; not
re-planned unless a v1 requirement above repairs them. Source: ingest intel
`requirements.md` + codebase map.

| ID | Capability | Milestone |
|----|------------|-----------|
| REQ-autosave-mod | Monthly autosave companion mod (achievement-compatible) | M1 |
| REQ-clausewitz-parser | Recursive Clausewitz text parser + ZIP unzipper | M1/M4 |
| REQ-file-watcher-live | `watchdog` watcher, debounce, `SAVE_CHANGED`/`GAME_PAUSED` | M4 |
| REQ-state-extractor-snapshot | Typed `GameSnapshot` via `StateExtractor` | M2/M3 |
| REQ-path-autodetect | Auto-detect EU4 install + Documents paths | M4 |
| REQ-advisor-top3 | Advisor mode, top-3 recommendations + risk alerts | M5/M6/M7 |
| REQ-execute-button | [Esegui] button delegating a single action (semi-bot) | M5/M8 |
| REQ-military-advisor | Military scoring, alerts, wartime logic | M6 |
| REQ-colonial-bot | Colonial bot (autonomous + target-list) | M7 |
| REQ-economy-advisor | Merchant steering + tech-timing alerts | M7 |
| REQ-action-executor | Mode-aware `ActionExecutor` (pyautogui) | M8 |
| REQ-auto-pause | Auto-pause on rebellion/war (Space, wired — PAUSE-01/02 done PR #15) | M5 |
| REQ-hotkey-toggle | F2 show/hide (wired — HOTKEY-01 done PR #15) | M5 |
| REQ-full-bot-states-params | Full-bot params + four states + instant off + control surface UI (PR #17) | M8 |
| REQ-colonial-bot-ranking | Colonial province ranking + COLONIST_IDLE fix (PR #17) | M7 |
| REQ-bot-error-handling | Critical vs minor bot error handling | M5/M8 |
| REQ-bot-pause-resume | Bot auto-pause/resume on stalled game | M4/M8 |
| REQ-activity-feed | Real-time activity feed in Advisor | M5 |
| REQ-log-export | Log filters + CSV export + JSONL telemetry | M1/M5 |
| REQ-changelog-on-update | Changelog shown on first launch after update | M10 |
| REQ-windows-standalone-build | PyInstaller `.exe` + CLI + GH Actions | M10 |
| REQ-no-crash-full-campaign | Stability across a full campaign | M9 |

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Ironman / binary Clausewitz parsing | Excluded for v1.0 by design; large separate effort |
| Live IPC/socket/API into EU4 | Game exposes no external API; file is the only channel |
| Automating peace / cession / indemnity | Safety policy: always manual confirmation |
| Italian-UI template matching | Match English base UI so translation mod cannot break recognition |
| Supported cross-platform GUI runtime | Windows is the target; Linux/macOS send-key paths stay experimental |
| Broad menu-navigation automation | Deferred to v2 (AUTO-01/02); out of this milestone |

## Traceability

Which phase covers which v1 requirement. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| LIVE-01 | Phase 1 | Done (PR #15) |
| LIVE-02 | Phase 1 | Done (PR #15) |
| LIVE-03 | Phase 1 | Done (PR #15) |
| LIVE-04 | Phase 1 | Done (PR #15) |
| PAUSE-01 | Phase 2 | Done (PR #15) |
| PAUSE-02 | Phase 2 | Done (PR #15) |
| HOTKEY-01 | Phase 2 | Done (PR #15) |
| HOTKEY-02 | Phase 2 | Done (PR #15) |
| SAFE-01 | Phase 3 | Done (PR #15) |
| SAFE-02 | Phase 3 | Done (PR #15) |
| SAFE-03 | Phase 3 | Done (PR #15) |
| SAFE-04 | Phase 3 | Done (PR #15) |
| BUILD-01 | Phase 4 | Done (PR #15) |
| BUILD-02 | Phase 4 | Done (PR #15) |
| BUILD-03 | Phase 4 | Done (PR #15) |

**Coverage:**
- v1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-23*
*Last updated: 2026-06-27 — tutte le 15 v1 req Done (PR #15); post-milestone PR #17 annotato; 181 test*
