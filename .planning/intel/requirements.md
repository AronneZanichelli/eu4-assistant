# Requirements (Intel)

Requirements extracted primarily from the authoritative SPEC's "Definition of Done" (§13)
and feature priority table (§4), cross-checked against CHANGELOG (what shipped) and README
(usage surface). No PRDs were present, so requirements are derived from the SPEC. Acceptance
criteria are taken from the SPEC's DoD checklist; "shipped" notes reference CHANGELOG/README.

Each requirement: ID, source, description, acceptance, scope.

---

## REQ-autosave-mod
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§8.9, §13)
- description: Monthly autosave companion mod that does not alter game rules and is
  achievement-compatible.
- acceptance: Mod forces monthly save via `on_monthly_pulse → save_game = yes`; documented;
  no gameplay mechanic changes.
- scope: mod
- shipped: CHANGELOG M1 (`ModBuilder` installs companion mod with monthly save trigger)

## REQ-clausewitz-parser
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.2, §8.2, §13)
- description: Recursive Clausewitz text parser + ZIP unzipper that correctly parses a
  normal campaign save with all DLC.
- acceptance: Handles nested blocks, scalar lists, anonymous block lists, quoted strings,
  `YYYY.MM.DD` dates; outputs native Python dict tree; ZIP decompression pre-parse.
- scope: parser
- shipped: CHANGELOG M1 (parser), M4 (`SaveUnzipper`)

## REQ-file-watcher-live
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.1, §8.1, §13)
- description: Live file watcher stable for an entire campaign, with 1–3s latency from save
  write to UI update.
- acceptance: `watchdog` watcher with 500ms debounce; thread-safe queue; emits
  `SaveChanged` and `GamePaused` (no new autosave within configurable timeout, default 3min).
- scope: watcher
- shipped: CHANGELOG M4 (`FileWatcher`, `SaveEvent` with `SAVE_CHANGED`/`GAME_PAUSED`)

## REQ-state-extractor-snapshot
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§8.3, §8.4, §9)
- description: Extract a typed `GameSnapshot` (economy, military, diplomacy, colonial, risk,
  tech, ideas, trade nodes, provinces) from the raw Clausewitz tree with defensive parsing.
- acceptance: Typed dataclasses with safe defaults; optional DLC sections handled; matches
  the §9 snapshot schema.
- scope: extractor / models
- shipped: CHANGELOG M2 (models), M3 (`StateExtractor`)

## REQ-path-autodetect
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.6, §13)
- description: Auto-detect EU4 install and Paradox Documents paths on first launch.
- acceptance: Finds Steam install + Documents folder; manual selection dialog fallback.
- scope: config
- shipped: CHANGELOG/DESIGN §8.10 (config M4)

## REQ-advisor-top3
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§3.1, §4, §8.5, §13)
- description: Advisor mode (default) showing top-3 contextual recommendations with
  human-readable "why" text, plus risk alerts; no automatic action.
- acceptance: Top-3 cards always visible (even without active alerts); each carries title,
  category, score, "why", `executable: bool`; alerts: AE, coalition, debt, manpower,
  rebels, war.
- scope: decision_engine / ui
- shipped: CHANGELOG M5 (`AdvisorPanel`), M6/M7 (eval logic)

## REQ-execute-button
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§3.1, §3.2, §13)
- description: An [Esegui] button on each executable recommendation delegating that single
  action to the bot (semi-bot), with a confirm dialog, then return to Advisor.
- acceptance: Button on every executable card; confirm dialog shows action detail; returns
  to Advisor after execution.
- scope: ui / executor
- shipped: CHANGELOG M5 (`execute_requested` signal), M8 (wired to executor)

## REQ-military-advisor
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§4, §8.5, §13)
- description: Military logic — peacetime stack scoring vs combat width + undersized-army
  alerts + recruitment; wartime routing, sieges, engage/retreat by battle odds.
- acceptance: Stack scoring; army-below-force-limit & fragmented-stack & wartime-manpower
  alerts; wartime movement/siege/engage/retreat functioning.
- scope: decision_engine / executor
- shipped: CHANGELOG M6 (`evaluate_military`, new `RiskCode`s, `WarState`)

## REQ-colonial-bot
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§4, §8.5, §13)
- description: Colonial bot with two operating modes — autonomous (rank provinces by
  value × safety and colonize) and target-list (player ticks provinces, bot colonizes in
  order). Active mode configurable and persisted.
- acceptance: Both modes functioning; province ranking; colonist dispatch; mode persisted.
- scope: decision_engine
- shipped: CHANGELOG M7 (`evaluate_colonial`, `COLONIST_IDLE`)

## REQ-economy-advisor
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§4, §8.5, §13)
- description: Economy advisor — merchant steering and tech-timing alerts (insufficient
  monarch points).
- acceptance: Merchant steering; alert on undeployed merchants and affordable/overflow tech.
- scope: decision_engine
- shipped: CHANGELOG M7 (`evaluate_economy_adv`, `MERCHANT_UNDEPLOYED`, `TECH_AFFORDABLE`)

## REQ-action-executor
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.5, §8.6, §13)
- description: Real action executor via pyautogui+win32api with pre/post checks, semi-bot
  confirm dialog, supervisor (retry/fallback/emergency stop), and live action banner.
- acceptance: Each handler does pre_check→execute→post_check; confirm dialog for semi-bot;
  live "Sto eseguendo: [azione]" banner; template matching on English UI.
- scope: executor
- shipped: CHANGELOG M8 (`ActionExecutor.execute()` mode-aware, pyautogui `[bot]` extra)

## REQ-auto-pause
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§5.1, §8.7, §13)
- description: Automatic EU4 pause (F1) on imminent rebellion and war declared.
- acceptance: F1 sent on `rebels_imminent` (max unrest) and `war_declared`; event logged;
  low priority, no stability impact.
- scope: pause_controller
- shipped: DESIGN §8.7 / CHANGELOG M5 (`PauseController`)

## REQ-hotkey-toggle
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§5.2, §8.8, §13)
- description: F2 (configurable) hotkey to show/hide the companion window.
- acceptance: F2 toggles window visibility globally.
- scope: ui
- shipped: CHANGELOG M5 (F2 hotkey; listener via pynput — see constraints/conflicts)

## REQ-full-bot-states-params
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§3.3, §5.5, §8.5, §13)
- description: Full-bot with configurable, persisted parameters; four distinct, visible
  states (active / paused / error / off); instant disable switch.
- acceptance: Params (budget, limits, enabled categories, colonial mode) persisted; four
  states visible; instant off switch.
- scope: ui / config
- shipped: CHANGELOG M8 (full-bot params UI)

## REQ-bot-error-handling
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§5.4, §13)
- description: Bot error handling distinguishing critical (game state possibly altered →
  stop, visual+audio notice, wait for explicit "Riprendi") vs minor (action not executed →
  stop, notice, auto-resume next autosave).
- acceptance: Red banner + audio + log badge; bot enters distinct `errore` state; critical
  vs minor handling per spec.
- scope: executor / ui

## REQ-bot-pause-resume
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§8.6, §13)
- description: Bot enters `pausa automatica` when EU4 is stopped (no new autosave after
  timeout) and auto-resumes on the next save.
- acceptance: Detects stalled game; shows "EU4 in pausa — bot in attesa"; auto-resume.
- scope: executor / watcher

## REQ-activity-feed
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§8.4b, §8.6, §13)
- description: Real-time activity feed of bot actions in the Advisor panel (compact banner
  above recommendation cards): action type, target, status.
- acceptance: Each executed action appears live with type/target/status (in corso /
  completata / fallita).
- scope: ui

## REQ-log-export
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§8.8, §8.11, §13)
- description: Chronological real-time event log with per-level filters and CSV export at
  session end; structured JSONL telemetry.
- acceptance: Log filters (decision/action/alert/error); CSV export; `events.jsonl`
  rotating log.
- scope: ui / telemetry
- shipped: CHANGELOG M5 (`LogPanel` with levels+filters), M1 (telemetry helpers)

## REQ-changelog-on-update
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§5.3, §8.11, §13)
- description: Show changelog on first launch after an update.
- acceptance: Changelog displayed on each update; tracked via `changelog_seen.txt`.
- scope: telemetry / config
- shipped: CHANGELOG M10 (changelog system)

## REQ-windows-standalone-build
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§13); README "Build"
- description: Standalone Windows executable with no external dependencies.
- acceptance: `pyinstaller eu4_assistant.spec --clean` → `dist/eu4-assistant.exe`
  (no console, standalone).
- scope: packaging
- shipped: CHANGELOG M10 (PyInstaller `.spec`, CLI entry point, GH Actions build on `v*`)

## REQ-no-crash-full-campaign
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§1, §13)
- description: No crash across a complete campaign (1444 → end).
- acceptance: Stability for full campaign duration; DLC regression covered.
- scope: cross-cutting / QA
- shipped: CHANGELOG M9 (QA, round-trip tests, UI tests)
