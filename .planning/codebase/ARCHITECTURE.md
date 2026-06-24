<!-- refreshed: 2026-06-23 -->
# Architecture

**Analysis Date:** 2026-06-23

## System Overview

The application is a **single-process desktop companion** for Europa Universalis IV. It watches the game's autosave file, parses it into a typed snapshot, evaluates risk and advice, and renders results in a 3-column PyQt6 window. Optional semi-/full-bot modes can send keystrokes to the game.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                        ENTRY / ORCHESTRATION                              │
│  CLI: `main.run()` (headless bootstrap)                                   │
│  UI : `main.run_with_ui()`  ── QApplication event loop + watcher thread   │
│        `eu4_assistant_bot/main.py`                                        │
└───────────────┬───────────────────────────────────────┬─────────────────┘
                │ (background daemon thread)              │ (Qt main thread)
                ▼                                         ▼
┌───────────────────────────────────┐     ┌─────────────────────────────────┐
│        INGESTION PIPELINE          │     │        PRESENTATION (UI)         │
│  FileWatcher  `watcher.py`         │     │  MainWindow `ui/main_window.py`  │
│  SaveUnzipper `save_unzipper.py`   │     │   ├ DashboardPanel (left ~25%)   │
│  ClausewitzTextParser `parser.py`  │     │   ├ AdvisorPanel   (center ~45%) │
│  StateExtractor `extractor.py`     │     │   └ LogPanel       (right ~30%)  │
└───────────────┬───────────────────┘     │  HotkeyManager `ui/hotkey.py`    │
                │ GameSnapshot              └──────────────▲──────────────────┘
                ▼                                          │ pyqtSignal (thread-safe)
┌───────────────────────────────────────────────────────┐│
│                   DECISION LAYER                        ││
│  DecisionEngine `decision_engine.py`                   ││
│   evaluate_risks → RiskAlerts                          │┘
│   recommend      → list[Recommendation] (top 3)        │
│   build_action_plans → list[ActionPlan]                │
└───────────────┬───────────────────────────────────────┘
                ▼
┌───────────────────────────────────────────────────────┐
│                  ACTION / OUTPUT LAYER                  │
│  ActionExecutor `executor.py`                          │
│   simulate() (ASSIST) | execute() (SEMI/FULL → keys)   │
│  PauseController `pause_controller.py` (auto-pause)     │
│  telemetry.emit_event → `~/.eu4-assistant/events.jsonl`│
└────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `FileWatcher` | Watchdog-based monitor of the autosave file; debounces writes; detects pause | `eu4_assistant_bot/watcher.py` |
| `SaveUnzipper` | Extract `gamestate` text from a `.eu4` ZIP (or plain-text) save | `eu4_assistant_bot/save_unzipper.py` |
| `ClausewitzTextParser` | Tokenize + recursively parse Clausewitz text → nested `dict` | `eu4_assistant_bot/parser.py` |
| `EU4RulesLoader` | Load unit/idea/modifier definitions from the EU4 install + mods | `eu4_assistant_bot/parser.py` |
| `StateExtractor` | Map raw parse tree → typed `GameSnapshot` (defensive) | `eu4_assistant_bot/extractor.py` |
| `GameSnapshot` + sub-states | Central typed game-state container (dataclasses) | `eu4_assistant_bot/models.py` |
| `DecisionEngine` | Risk evaluation, prioritized recommendations, action plans | `eu4_assistant_bot/decision_engine.py` |
| `ActionExecutor` | Simulate (ASSIST) or execute (SEMI/FULL) action plans via keystrokes | `eu4_assistant_bot/executor.py` |
| `PauseController` | Auto-pause EU4 (F1) on rebels/war (standalone, not yet wired) | `eu4_assistant_bot/pause_controller.py` |
| `MainWindow` | 3-column PyQt6 window; thread-safe signal sink for the pipeline | `eu4_assistant_bot/ui/main_window.py` |
| `AppConfig` / `build_config` | Modes, risk profiles, paths, thresholds, data-dir bootstrap | `eu4_assistant_bot/config.py` |
| `ModBuilder` | Generate/install the monthly-autosave EU4 mod | `eu4_assistant_bot/mod/mod_builder.py` |
| `SnapshotReader` / `SaveSnapshotAdapter` | Legacy bridges: JSON snapshot / `key=value` extract → `GameSnapshot` | `eu4_assistant_bot/state_reader.py`, `eu4_assistant_bot/save_adapter.py` |
| `telemetry` | Rotating-file logging + JSONL event log | `eu4_assistant_bot/telemetry.py` |

## Pattern Overview

**Overall:** Layered **pipeline / producer-consumer** with a thin orchestration layer.

**Key Characteristics:**
- **Unidirectional data flow:** raw bytes → text → dict tree → `GameSnapshot` → alerts/recommendations/plans → UI/keystrokes. Each stage has a single, well-typed output.
- **`GameSnapshot` as the integration contract:** every layer downstream of extraction depends only on `models.py`, never on the parser internals. Multiple producers (live save, legacy JSON, legacy `key=value`) converge on the same `GameSnapshot`.
- **Producer/consumer across threads:** `FileWatcher` produces `SaveEvent`s on a `queue.Queue`; the watcher loop consumes them, runs the pipeline, and pushes results into Qt via signals (the only safe cross-thread channel).
- **Defensive extraction:** `StateExtractor` and the legacy readers never raise on missing/malformed fields — they fall back to dataclass defaults.
- **Config-driven behavior:** `BotMode` and `RiskProfile` select preset `SafetyLimits` / `DecisionThresholds`; the engine and executor read these rather than hard-coding policy.

## Layers

**Orchestration / Entry (`main.py`):**
- Purpose: parse CLI args, build config, set up logging, and start either the headless bootstrap (`run`) or the live UI pipeline (`run_with_ui`).
- Location: `eu4_assistant_bot/main.py`
- Depends on: every other layer (it wires them together).
- Used by: `__main__.py`, the `eu4-assistant` console script, the PyInstaller entry.

**Ingestion Pipeline (`watcher` → `save_unzipper` → `parser` → `extractor`):**
- Purpose: turn an on-disk `.eu4` file into a typed `GameSnapshot`.
- Location: `eu4_assistant_bot/watcher.py`, `save_unzipper.py`, `parser.py`, `extractor.py`.
- Depends on: `watchdog` (watcher), stdlib `zipfile` (unzipper), `models.py` (extractor).
- Used by: `run_with_ui()`'s `_process_save` closure.

**Decision Layer (`decision_engine.py`):**
- Purpose: pure analysis. Convert a `GameSnapshot` into `RiskAlerts`, ranked `Recommendation`s (top 3), and `ActionPlan`s.
- Location: `eu4_assistant_bot/decision_engine.py`.
- Depends on: `models.py`, `config.DecisionThresholds`. No I/O, no Qt.
- Used by: `main.run`, `main.run_with_ui`, and (for execution) `MainWindow`.

**Action / Output Layer (`executor.py`, `pause_controller.py`, `telemetry.py`):**
- Purpose: act on plans (simulate or send keystrokes), auto-pause on emergencies, and record telemetry.
- Location: `eu4_assistant_bot/executor.py`, `pause_controller.py`, `telemetry.py`.
- Depends on: `pyautogui` (executor, optional), `xdotool`/`pynput` (pause controller, optional).
- Used by: `MainWindow._on_execute_requested` (executor), `main.run` (telemetry).

**Presentation (`ui/`):**
- Purpose: render snapshot/recommendations/alerts/log; capture the Esegui (execute) intent and the F2 toggle.
- Location: `eu4_assistant_bot/ui/`.
- Depends on: `PyQt6`, `pynput` (hotkey), and the typed objects from `models.py` / `decision_engine.py`.
- Used by: `run_with_ui()`.

## Data Flow

### Primary Request Path (live save → UI)

1. Game writes the autosave; OS fires a filesystem event. `_SaveFileHandler.on_modified` debounces (0.5 s) and calls back (`eu4_assistant_bot/watcher.py:54`).
2. `FileWatcher._on_save_changed` enqueues a `SAVE_CHANGED` `SaveEvent` (`eu4_assistant_bot/watcher.py:163`).
3. The watcher loop dequeues the event and calls `_process_save(path)` (`eu4_assistant_bot/main.py:230`).
4. `SaveUnzipper.extract_gamestate` returns the gamestate text (`eu4_assistant_bot/save_unzipper.py:29`).
5. `ClausewitzTextParser.parse_text` tokenizes and builds the nested dict tree (`eu4_assistant_bot/parser.py:182`).
6. `StateExtractor.extract` produces a typed `GameSnapshot` (`eu4_assistant_bot/extractor.py:39`).
7. `DecisionEngine.evaluate_risks` / `recommend` / `build_action_plans` analyze it (`eu4_assistant_bot/decision_engine.py:90`, `:289`, `:430`).
8. Results are pushed to the window via `push_snapshot` / `push_recommendations` / `push_alerts` / `push_plans`, each emitting a `pyqtSignal` so the Qt thread updates the panels (`eu4_assistant_bot/main.py:212`, `eu4_assistant_bot/ui/main_window.py:119`).

### Execute Path (user-triggered action)

1. User clicks **Esegui** on a recommendation card; `_RecommendationCard` emits its category (`eu4_assistant_bot/ui/advisor_panel.py:65`).
2. `MainWindow._on_execute_requested` checks mode; in SEMI_BOT it shows a confirm dialog (`eu4_assistant_bot/ui/main_window.py:160`).
3. `ActionExecutor.execute` logs the advisory and, for SEMI/FULL, calls `_pause_game()` to send `space` via `pyautogui` (`eu4_assistant_bot/executor.py:77`).
4. Results are appended to the `LogPanel`.

### Headless Bootstrap Path (`run`)

1. Build config, set up logging, load the rules index via `EU4RulesLoader` (`eu4_assistant_bot/main.py:43`).
2. Acquire a `GameSnapshot` from JSON (`SnapshotReader`), from a `key=value` extract (`SaveSnapshotAdapter`), or empty fallback (`eu4_assistant_bot/main.py:48`).
3. Persist it to `~/.eu4-assistant/snapshots/last_snapshot.json` (`models.GameSnapshot.save`).
4. Run engine + `ActionExecutor.simulate`, then `telemetry.emit_event("startup", …)` to `events.jsonl` (`eu4_assistant_bot/main.py:79`).

**State Management:**
- No global mutable state. `GameSnapshot` is the per-cycle state object; it is recreated on every save.
- Cross-thread state moves only through the watcher's `queue.Queue` and Qt signals. `MainWindow._current_plans` is the only retained mutable field, updated exclusively on the Qt thread via `_on_plans`.
- Persistence is file-based under `~/.eu4-assistant/` (logs, snapshots, `events.jsonl`) and Qt `QSettings` for window geometry.

## Key Abstractions

**`GameSnapshot` (the central contract):**
- Purpose: typed, defaulted representation of one save tick. Composed of `EconomyState`, `MilitaryState` (with `ArmyState`), `DiplomacyState`, `ColonialState`, `RiskState`, `WarState`, `TechState`, `IdeasState`, plus lists of `TradeNodeState` and `ProvinceState`.
- Examples: `eu4_assistant_bot/models.py:111` (class), `:132` (`empty()`), `:137` (`to_json`), `:140` (`save`).
- Pattern: `@dataclass(slots=True)` with `field(default_factory=...)` for every sub-state so missing save fields never crash downstream code.

**`RiskAlerts` / `RiskReason` / `RiskCode`:**
- Purpose: explainable risk output. Booleans for quick UI badges plus a `reasons` list carrying `code`, `severity`, `message`, `current_value`, `threshold_value`.
- Examples: `eu4_assistant_bot/decision_engine.py:43` (`RiskAlerts`), `:55` (`RiskCode`), `:71` (`RiskReason`).
- Pattern: enum-coded, human-readable reasons make alerts traceable from UI back to thresholds.

**`Recommendation` / `ActionPlan` / `ExecutionResult`:**
- Purpose: advice → executable plan → result. `recommend()` ranks and truncates to top 3; `build_action_plans()` maps each to an `ActionPlan`; `ActionExecutor` returns `ExecutionResult`s.
- Examples: `eu4_assistant_bot/decision_engine.py:35`, `eu4_assistant_bot/models.py:145`, `eu4_assistant_bot/executor.py:34`.

**`BotMode` / `RiskProfile` + preset maps:**
- Purpose: declarative policy. `MODE_PRESETS` → `SafetyLimits`; `RISK_PROFILE_PRESETS` → `DecisionThresholds`.
- Examples: `eu4_assistant_bot/config.py:14`, `:20`, `:70`, `:109`, `build_config` at `:116`.

**`SaveEvent` / `SaveEventType`:**
- Purpose: the producer/consumer message between watcher threads and the loop.
- Examples: `eu4_assistant_bot/watcher.py:27`, `:32`.

## Entry Points

**`main()` (console script `eu4-assistant`):**
- Location: `eu4_assistant_bot/main.py:260`; also reachable via `python -m eu4_assistant_bot` (`eu4_assistant_bot/__main__.py`).
- Triggers: CLI invocation. `--watch SAVE_PATH` → `run_with_ui`; otherwise `run`.
- Responsibilities: parse args (`--mode`, `--risk-profile`, `--install-path`, `--snapshot-json`, `--snapshot-save`, `--watch`), build mode/profile enums, dispatch.

**`run(...)` (headless bootstrap):**
- Location: `eu4_assistant_bot/main.py:28`.
- Triggers: CLI without `--watch`. Used heavily by tests (`tests/test_bootstrap.py`).
- Responsibilities: rules load, snapshot acquisition (JSON / extract / empty), engine + simulated executor, telemetry emit.

**`run_with_ui(...)` (live UI pipeline):**
- Location: `eu4_assistant_bot/main.py:151`.
- Triggers: `--watch`. Requires the `[ui]`/`[bot]` extra (PyQt6 imported lazily).
- Responsibilities: start `QApplication` + `MainWindow`, spawn the daemon watcher thread running `_watcher_loop`, route each save through the pipeline into the UI.

**PyInstaller entry:**
- `eu4_assistant.spec` builds `dist/eu4-assistant.exe` from `eu4_assistant_bot/main.py` with `ui`, `mod`, PyQt6, and watchdog as hidden imports.

## Architectural Constraints

- **Threading model:** Qt runs on the main thread; the file watcher runs `watchdog`'s observer thread plus a `eu4-pause-monitor` thread, and `run_with_ui` adds a dedicated daemon `eu4-watcher` loop thread. **All UI mutation must cross into the Qt thread via `pyqtSignal`** (see `MainWindow.push_*` → signal → `@pyqtSlot`). Calling Qt widget methods directly from the watcher thread is forbidden. `LogPanel.add_entry` is the lone exception currently called directly via `push_log` — keep log writes simple/atomic.
- **Optional native deps are import-guarded:** `PyQt6` is imported lazily inside `run_with_ui` (`eu4_assistant_bot/main.py:166`); `pyautogui` inside `ActionExecutor._pause_game` (`eu4_assistant_bot/executor.py:133`); `pynput`/`xdotool` inside `PauseController._default_send_key` (`eu4_assistant_bot/pause_controller.py:110`). Core ingestion + decision layers must remain importable with only `watchdog` installed.
- **Global state:** none at module scope beyond module-level constants and logger instances. Do not introduce module-level singletons holding game state.
- **Circular imports:** none. Dependency direction is strictly one-way: `ui/` and `main` depend on `decision_engine`/`models`; `decision_engine` depends on `models`/`config`; `models`/`config` depend on nothing internal. Preserve this — `models.py` must never import from any other package module.
- **Binary saves out of scope:** `SaveUnzipper` handles ZIP and plain-text only; Ironman binary saves are explicitly unsupported (`eu4_assistant_bot/save_unzipper.py:5`).
- **Platform target:** Windows-first (PyInstaller `.exe`, `pyautogui`), with Linux pause support via `xdotool`.

## Anti-Patterns

### Touching Qt widgets from the watcher thread

**What happens:** the pipeline runs in the `eu4-watcher` daemon thread; a tempting shortcut is to call `self.dashboard.update_snapshot(...)` directly from `_process_save`.
**Why it's wrong:** Qt widgets are not thread-safe; cross-thread widget calls cause intermittent crashes and corrupted painting.
**Do this instead:** push data through `MainWindow.push_*`, which emits a `pyqtSignal` routed to a `@pyqtSlot` on the Qt thread (`eu4_assistant_bot/ui/main_window.py:119`–`157`).

### Broad `except (SaveFormatError, Exception)` in the pipeline

**What happens:** `_process_save` catches `Exception` wholesale to keep the watcher loop alive (`eu4_assistant_bot/main.py:203`).
**Why it's wrong:** it masks programming errors (e.g. an `AttributeError` in the engine) as "parse failures," making bugs invisible.
**Do this instead:** catch `SaveFormatError` (and other known parse errors) specifically; let unexpected exceptions surface or log them with full tracebacks distinct from parse warnings.

### Adding fields to `GameSnapshot` without a default

**What happens:** new save data is modeled as a required dataclass field.
**Why it's wrong:** `StateExtractor`, `SnapshotReader`, and `SaveSnapshotAdapter` all rely on every field being defaultable so partial/legacy sources still construct a snapshot.
**Do this instead:** give every new field a safe default or `field(default_factory=...)`, matching the existing pattern in `eu4_assistant_bot/models.py`.

### Reaching into the parser dict from outside the extractor

**What happens:** consumers read raw keys like `tree["countries"][tag]["treasury"]` directly.
**Why it's wrong:** it couples business logic to the Clausewitz layout and bypasses the defensive coercion in `StateExtractor`.
**Do this instead:** add an extraction method on `StateExtractor` and expose the value through `GameSnapshot` (`eu4_assistant_bot/extractor.py`).

## Error Handling

**Strategy:** fail-soft in ingestion and analysis; surface a friendly message in the UI; never let one bad save kill the watcher loop.

**Patterns:**
- Typed domain exceptions for I/O boundaries: `SaveFormatError` (`save_unzipper.py:14`), `SaveAdapterError` (`save_adapter.py:15`), `SnapshotReadError` (`state_reader.py:28`). Each carries a descriptive message.
- `run()` wraps snapshot acquisition in try/except and falls back to `GameSnapshot.empty()` with a logged warning (`eu4_assistant_bot/main.py:48`–`65`).
- Extraction never raises: `StateExtractor` coercion helpers `_str`/`_float`/`_int`/`_dig` swallow `TypeError`/`ValueError` and return defaults (`eu4_assistant_bot/extractor.py:299`–`321`).
- Optional-dependency failures degrade to advisory-only and log a warning rather than crashing (`executor.py:134`, `pause_controller.py:120`).

## Cross-Cutting Concerns

**Logging:** `telemetry.setup_logging` configures a rotating file handler (`~/.eu4-assistant/logs/eu4-assistant.log`, 5 MB ×3) plus console, with `force=True` (`eu4_assistant_bot/telemetry.py:24`). Modules use `logging.getLogger(__name__)`.
**Telemetry / events:** `telemetry.emit_event` appends JSONL records to `~/.eu4-assistant/events.jsonl`, serializing enums via `_json_default` (`eu4_assistant_bot/telemetry.py:41`).
**Validation:** centralized in `DecisionThresholds.__post_init__`, which range-checks every threshold and raises `ValueError` on bad config (`eu4_assistant_bot/config.py:43`).
**Configuration:** `build_config(mode, risk_profile)` resolves home-relative paths lazily, copies presets via `dataclasses.replace`, and bootstraps the data directories (`eu4_assistant_bot/config.py:116`).
**Concurrency:** `queue.Queue` + `threading.Timer` debounce + `threading.Lock` around `_last_change` in the watcher; Qt `pyqtSignal` for thread-safe UI hand-off.

---

*Architecture analysis: 2026-06-23*
