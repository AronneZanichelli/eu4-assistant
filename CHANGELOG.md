# Changelog

All notable changes to EU4 Assistant Bot are documented here.

## [0.5.0] — 2026-03-17

### M10 — Packaging
- PyInstaller `.spec` file for Windows standalone executable (`eu4-assistant.exe`)
- CLI entry point `eu4-assistant` via `[project.scripts]`
- Added optional `[pkg]` extra: `pyinstaller>=5.0,<7.0`
- GitHub Actions build workflow (`.github/workflows/build.yml`) triggered on `v*` tags
- Fixed version mismatch: `__init__.py` now correctly reports `0.5.0`

### M9 — QA & Round-trip
- `SnapshotReader.read_json_snapshot()` now reconstructs `trade_nodes` as
  `list[TradeNodeState]` and `provinces` as `list[ProvinceState]` (JSON round-trip complete)
- 3 new round-trip tests in `tests/test_state_reader.py`
- 4 new `MainWindow` M8 tests in `tests/test_ui.py`
  (`test_set_mode_updates_label`, `test_push_plans_stores_plans`,
  `test_execute_requested_assist_mode_noop`, `test_execute_requested_no_plans`)

### M8 — UI-Pipeline Integration
- `run_with_ui()` in `main.py`: live `FileWatcher` → `DecisionEngine` → `MainWindow`
  pipeline running in a daemon thread
- `ActionExecutor.execute()`: mode-aware execution
  (ASSIST=advisory, SEMI_BOT=confirm dialog + pyautogui pause, FULL_BOT=direct execute)
- `MainWindow`: `push_plans()`, `set_mode()`, `_on_execute_requested()` wired to executor
- Optional `[bot]` extra: `pyautogui>=0.9,<1.0` for game interaction
- `--watch SAVE_PATH` CLI flag for UI mode

### M7 — Colonial & Economy Advisor
- `DecisionEngine.evaluate_colonial()`: alert when colonists idle, ranks free provinces
- `DecisionEngine.evaluate_economy_adv()`: alert on undeployed merchants and tech overflow
- New `RiskCode` values: `COLONIST_IDLE`, `MERCHANT_UNDEPLOYED`, `TECH_AFFORDABLE`
- `RiskAlerts` extended with `colonial_risk` and `economy_adv_risk` flags

### M6 — Military Logic
- `DecisionEngine.evaluate_military()`: army size vs force limit, fragmented stack
  detection, wartime manpower alert
- New `RiskCode` values: `ARMY_BELOW_FORCE_LIMIT`, `ARMY_FRAGMENTED`,
  `WARTIME_MANPOWER_LOW`
- `WarState` model and `StateExtractor._extract_war()` integration
- `DecisionThresholds` extended: `army_strength_threshold`, `wartime_manpower_min`
- `RISK_PROFILE_PRESETS` updated for SAFE/BALANCED/AGGRESSIVE military thresholds

### M5 — PyQt6 UI
- `MainWindow`: 3-column layout (Dashboard | Advisor | Log), dark theme, F2 hotkey
- `DashboardPanel`: country/date/stability/prestige/legitimacy labels, manpower progress bar
- `AdvisorPanel`: top-3 recommendation cards with priority badge, alert badges,
  mode label, Esegui button with `execute_requested` signal
- `LogPanel`: timestamped log entries with `ALERT/DECISION/ACTION/ERROR` levels and
  per-level filters
- `PauseController`: hotkey listener via pynput
- Offscreen CI support (`QT_QPA_PLATFORM=offscreen`, `libegl1` system dependency)

### M4 — File Watcher
- `FileWatcher` (watchdog): monitors `.eu4` autosave files, emits `SaveEvent` with
  `SAVE_CHANGED` / `GAME_PAUSED` types
- `SaveUnzipper`: extracts `gamestate` text from `.eu4` zip archives
- Configurable poll interval and pause timeout

### M3 — State Extractor
- `StateExtractor`: walks `ClausewitzTextParser` AST to populate `GameSnapshot`
- Extracts economy, military (armies), diplomacy (AE map, alliances, truces, active wars),
  colonial, risk (coalition, rebels), tech (adm/dip/mil points), ideas, trade nodes,
  provinces

### M2 — State Reader & Models
- `GameSnapshot` and all sub-models (`EconomyState`, `MilitaryState`, `DiplomacyState`,
  `ColonialState`, `RiskState`, `TechState`, `IdeasState`, `TradeNodeState`,
  `ProvinceState`, `ArmyState`, `WarState`) as `@dataclass(slots=True)` with safe defaults
- `SnapshotReader`: JSON snapshot loader with `_safe_dict()` null tolerance
- `SaveSnapshotAdapter`: legacy key=value format reader
- `GameSnapshot.save()`: persists snapshot to JSON

### M1 — Foundation
- `ClausewitzTextParser`: recursive descent parser for EU4 Clausewitz save format
- `EU4RulesLoader`: indexes unit, idea, and modifier files from EU4 install path
- `DecisionEngine` scaffold: `evaluate_risks()`, `recommend()`, `build_action_plans()`
- `ActionExecutor.simulate()`: mode-aware simulation (ASSIST skips, SEMI_BOT/FULL_BOT execute)
- `AppConfig`, `BotMode`, `RiskProfile`, `DecisionThresholds`, `SafetyLimits`,
  `RISK_PROFILE_PRESETS`
- `ModBuilder`: installs the `eu4_assistant` companion mod with monthly save trigger
- `emit_event()` / `setup_logging()` telemetry helpers
- CI: GitHub Actions matrix (Python 3.11, 3.12) with pytest offscreen mode
