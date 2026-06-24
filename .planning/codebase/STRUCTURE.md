# Codebase Structure

**Analysis Date:** 2026-06-23

## Directory Layout

```text
eu4-assistant/
├── eu4_assistant_bot/             # Main package (all runtime code)
│   ├── __init__.py                # Public API re-exports + __version__
│   ├── __main__.py                # `python -m eu4_assistant_bot` → main()
│   ├── main.py                    # CLI + run()/run_with_ui() orchestration
│   ├── config.py                  # BotMode, RiskProfile, thresholds, AppConfig
│   ├── models.py                  # GameSnapshot + all typed sub-state dataclasses
│   ├── watcher.py                 # FileWatcher (watchdog) + SaveEvent queue
│   ├── save_unzipper.py           # .eu4 ZIP/plain → gamestate text
│   ├── parser.py                  # ClausewitzTextParser + EU4RulesLoader
│   ├── extractor.py               # parse tree → GameSnapshot
│   ├── decision_engine.py         # risk eval, recommendations, action plans
│   ├── executor.py                # ActionExecutor (simulate / execute)
│   ├── pause_controller.py        # auto-pause EU4 on rebels/war (standalone)
│   ├── state_reader.py            # JSON snapshot → GameSnapshot (legacy bridge)
│   ├── save_adapter.py            # key=value extract → GameSnapshot (legacy)
│   ├── telemetry.py               # logging setup + JSONL event emit
│   ├── ui/                        # PyQt6 presentation subpackage
│   │   ├── __init__.py            # exports MainWindow
│   │   ├── main_window.py         # 3-column MainWindow + signal wiring
│   │   ├── dashboard_panel.py     # left column: live game state
│   │   ├── advisor_panel.py       # center column: recs + alert badges
│   │   ├── log_panel.py           # right column: event feed + CSV export
│   │   └── hotkey.py              # F2 global hotkey (pynput)
│   └── mod/                       # EU4 monthly-autosave mod generator
│       ├── __init__.py            # exports ModBuilder + result types
│       └── mod_builder.py         # writes .mod descriptor, event, on_actions
├── tests/                         # pytest suite (mirrors module names)
│   ├── conftest.py                # shared fixtures (sample_save_zip, fixtures_dir)
│   ├── fixtures/                  # sample .eu4 text saves
│   │   ├── sample_flat.eu4.txt
│   │   └── sample_nested.eu4.txt
│   └── test_*.py                  # one file per module under test
├── .github/workflows/            # CI (ci.yml) + build (build.yml)
├── pyproject.toml                # setuptools metadata, extras, pytest config
├── eu4_assistant.spec            # PyInstaller spec → dist/eu4-assistant.exe
├── EU4_ASSISTANT_BOT_DESIGN.md   # design doc (milestones M1–M8)
├── CHANGELOG.md
├── README.md
└── LICENSE
```

## Directory Purposes

**`eu4_assistant_bot/` (package root):**
- Purpose: all runtime code. Flat module layout — one file per concern in the pipeline.
- Contains: orchestration (`main.py`), config, models, and the pipeline/decision/output modules.
- Key files: `main.py`, `models.py`, `decision_engine.py`.

**`eu4_assistant_bot/ui/` (presentation subpackage):**
- Purpose: PyQt6 desktop window and all widgets. The only place that imports `PyQt6`.
- Contains: the `MainWindow` shell plus the three column panels and the global hotkey manager.
- Key files: `main_window.py` (owns layout, signals, executor wiring), `advisor_panel.py`, `dashboard_panel.py`, `log_panel.py`.

**`eu4_assistant_bot/mod/` (mod generator subpackage):**
- Purpose: generate and idempotently install a minimal EU4 mod that forces a monthly autosave (so the watcher always has fresh data).
- Contains: `ModBuilder` and the embedded `.mod`/event/on_actions templates.
- Key files: `mod_builder.py`.

**`tests/`:**
- Purpose: pytest suite. Naming mirrors source modules (`test_<module>.py`).
- Contains: unit tests for parser, extractor, decision engine, executor, watcher, config, adapters, UI, mod builder, plus a `test_bootstrap.py` covering `main.run`.
- Key files: `conftest.py` (fixtures), `fixtures/sample_*.eu4.txt` (parser inputs).

**`.github/workflows/`:**
- Purpose: CI (`ci.yml`) and standalone-build (`build.yml`) automation.
- Generated: No. Committed: Yes.

## Key File Locations

**Entry Points:**
- `eu4_assistant_bot/main.py`: `main()` (CLI), `run()` (headless), `run_with_ui()` (live UI). Console script `eu4-assistant` → `main`.
- `eu4_assistant_bot/__main__.py`: enables `python -m eu4_assistant_bot`.
- `eu4_assistant.spec`: PyInstaller build entry (`eu4_assistant_bot/main.py`).

**Configuration:**
- `eu4_assistant_bot/config.py`: `BotMode`, `RiskProfile`, `DecisionThresholds`, `SafetyLimits`, `AppConfig`, `build_config`.
- `pyproject.toml`: package metadata, dependency extras (`ui`, `bot`, `dev`, `pkg`), `[tool.pytest.ini_options]`.

**Core Logic:**
- Ingestion: `eu4_assistant_bot/watcher.py`, `save_unzipper.py`, `parser.py`, `extractor.py`.
- Decision: `eu4_assistant_bot/decision_engine.py`.
- Output: `eu4_assistant_bot/executor.py`, `pause_controller.py`, `telemetry.py`.
- Data model (the contract): `eu4_assistant_bot/models.py`.

**Testing:**
- `tests/conftest.py`, `tests/fixtures/`, and `tests/test_*.py`.

## Naming Conventions

**Files:**
- Modules: `snake_case.py`, named after the primary class/concern (`decision_engine.py` → `DecisionEngine`).
- Tests: `test_<module>.py`, one per source module.
- Fixtures: `sample_<shape>.eu4.txt` (e.g. `sample_nested.eu4.txt`).

**Directories:**
- Packages: `snake_case` (`eu4_assistant_bot`, `ui`, `mod`).

**Code symbols:**
- Classes: `PascalCase` (`GameSnapshot`, `FileWatcher`, `ClausewitzTextParser`).
- Functions/methods/vars: `snake_case` (`evaluate_risks`, `build_action_plans`).
- Module-private helpers: leading underscore (`_tokenize`, `_parse_block`, `_RecommendationCard`, `_SaveFileHandler`).
- Tunable constants: `UPPER_SNAKE` with `_` prefix when module-private (`_PRIO_COALITION`, `_REBEL_RISK_PER_FACTION`, `_MERCHANT_NODE_MIN_VALUE`).
- Enums: `str`-mixed enums for serializability (`class BotMode(str, Enum)`, `RiskCode`, `LogLevel`, `SaveEventType`).
- Dataclasses: `@dataclass(slots=True)` is the default for state/value types.

## Where to Add New Code

**New game metric / snapshot field:**
- Add a defaulted field to the relevant sub-state (or a new sub-state) in `eu4_assistant_bot/models.py`.
- Populate it defensively in `eu4_assistant_bot/extractor.py` (use the `_str`/`_float`/`_int`/`_dig` helpers).
- If it should round-trip from JSON/extracts, extend `eu4_assistant_bot/state_reader.py` (and `save_adapter.py` if relevant).
- Surface it in the UI via `eu4_assistant_bot/ui/dashboard_panel.py`.

**New risk / recommendation:**
- Add a `RiskCode` enum value and an evaluation branch in `eu4_assistant_bot/decision_engine.py` (mirror the `evaluate_military` / `evaluate_colonial` pattern).
- Add the matching `Recommendation` in `recommend()` and, if executable, a branch in `_map_recommendation_to_action` plus a description in `executor.py`'s `_ACTION_DESCRIPTIONS`.
- Tune priority via a new `_PRIO_*` constant at the top of `decision_engine.py`.
- Add a threshold to `DecisionThresholds` (with range validation in `__post_init__`) and to each preset in `RISK_PROFILE_PRESETS` if profile-dependent.

**New UI panel / widget:**
- Implementation: `eu4_assistant_bot/ui/<panel>.py` as a `QWidget` subclass.
- Wire it in `eu4_assistant_bot/ui/main_window.py` (add to the `QHBoxLayout`, add a `push_*`/signal/slot pair for thread-safe updates).

**New executor action:**
- Add the action branch in `decision_engine._map_recommendation_to_action`, a description in `executor._ACTION_DESCRIPTIONS`, and handling in `ActionExecutor.execute`/`simulate`.

**New file-ingestion source:**
- Mirror `state_reader.py` / `save_adapter.py`: a small reader class that returns a `GameSnapshot`, wired into `main.run` argument handling.

**Tests:**
- Add `tests/test_<module>.py`; reuse `conftest.py` fixtures (`sample_save_zip`, `fixtures_dir`) and add fixture files under `tests/fixtures/` for parser/extractor inputs.

## Special Directories

**`eu4_assistant_bot.egg-info/`:**
- Purpose: setuptools editable-install metadata.
- Generated: Yes. Committed: No (build artifact).

**`.venv/`:**
- Purpose: local virtual environment.
- Generated: Yes. Committed: No.

**`__pycache__/` (multiple):**
- Purpose: Python bytecode cache.
- Generated: Yes. Committed: No.

**`~/.eu4-assistant/` (runtime, outside repo):**
- Purpose: created at runtime by `AppConfig.bootstrap_dirs`. Holds `logs/`, `snapshots/`, `events.jsonl`, and `session_log.csv`.
- Generated: Yes (at runtime). Committed: No.

---

*Structure analysis: 2026-06-23*
