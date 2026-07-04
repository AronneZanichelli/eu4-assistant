# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

EU4 Assistant + Bot — desktop companion for Europa Universalis IV. It watches EU4 autosaves, parses them into a typed `GameSnapshot`, and produces risk alerts + recommendations through a PyQt6 UI, with optional action automation (semi/full-bot).

## Commands

The local interpreter is **not** on `PATH` as `python`; use the venv directly. UI tests construct a `QApplication`, so `QT_QPA_PLATFORM=offscreen` is **required** for the suite to run headless.

```bash
# Install (dev = test deps + PyQt6; runtime extras: [ui], [bot], [pkg])
.venv/bin/python -m pip install -e ".[dev]"

# Full test suite
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q

# Single file / single test or class
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_decision_engine.py -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest tests/test_ui.py::TestMainWindow -q

# Run one-shot analysis (no UI) from a snapshot
.venv/bin/python -m eu4_assistant_bot --mode assist --snapshot-json snapshot.json

# Run live UI with file watcher on a real save
.venv/bin/python -m eu4_assistant_bot --mode semi-bot --watch path/to/autosave.eu4

# Build standalone Windows exe
.venv/bin/python -m pip install -e ".[bot,pkg]" && pyinstaller eu4_assistant.spec --clean
```

**Version targets:** CI runs Python **3.11 / 3.12** (`.github/workflows/ci.yml`); the local `.venv` is 3.14. Do **not** rely on 3.13+ syntax even though it runs locally. `pynput`/`pyautogui` are optional runtime backends, absent in dev — code lazy-imports them and degrades gracefully, so the suite passes without them.

## Architecture

The whole pipeline funnels save data into one central typed object, `models.GameSnapshot` (slots dataclass with safe-empty defaults), which every downstream stage consumes.

**Two entry paths**, both in `main.py`:

1. `run()` — one-shot CLI: `build_config` → `EU4RulesLoader.load_rules_index` → read snapshot (`SnapshotReader` JSON / `SaveSnapshotAdapter` key=value / `GameSnapshot.empty` fallback) → `DecisionEngine` → `ActionExecutor.simulate` → append a structured event to `events.jsonl`.
2. `run_with_ui()` — live mode: a background `FileWatcher` thread fires on each new save → `_save_to_snapshot` (`SaveUnzipper` → `ClausewitzTextParser.parse_text` → `StateExtractor.extract`) → `DecisionEngine` → `PauseController.check` (auto-pauses EU4 via F1 on rebels/war) → results pushed to `MainWindow` via Qt signals. Optional `[ui]`/`[bot]` extras; all PyQt6 imports are deferred to call time so `run()` works without them.

**Decision core:** `DecisionEngine` (`decision_engine.py`) takes a snapshot + `DecisionThresholds` and returns three typed lists/objects — `RiskAlerts`, `list[Recommendation]`, `list[ActionPlan]`. `ActionExecutor` (`executor.py`) turns plans into `ExecutionResult`s: `simulate()` for ASSIST/tests, `execute()` for the real pyautogui path.

**Config composition** (`config.py`): `build_config(mode, risk_profile)` is the single entry point. It composes an `AppConfig` from two preset dicts keyed by enum — `MODE_PRESETS` (per-`BotMode` `SafetyLimits`) and `RISK_PROFILE_PRESETS` (per-`RiskProfile` `DecisionThresholds`). To add a mode/profile, extend the enum **and** its preset dict. `BotParams` (persisted to `~/.eu4-assistant/bot_params.json`) holds the user-tunable full-bot knobs edited by the params panel; its load/save is deliberately Qt-free so it's testable headless.

**UI** (`ui/`): three-column `MainWindow` (dashboard / advisor / log). Slots/handlers (`_on_snapshot`, `_on_execute_requested`, `push_*`) are the integration seams — tests call them directly rather than spinning a Qt event loop.

## Conventions

Full detail in `.planning/codebase/` (`CONVENTIONS.md`, `TESTING.md`, `ARCHITECTURE.md`). Non-obvious points:

- **`from __future__ import annotations` in every module** (required for PEP 604 `X | None` on 3.11).
- **`@dataclass(slots=True)` is the default** for all models; mutable defaults via `field(default_factory=...)`; validation in `__post_init__` raising `ValueError(f"... got {value}")`.
- **`str`-mixin enums** (`class Foo(str, Enum)`) for modes/codes/event types so they serialize as their value; CLI choices are generated from the enum, never hardcoded.
- **Dependency injection over mocking.** No `unittest.mock` anywhere — side-effecting callables (key senders, callbacks) are constructor params; tests pass a list's `.append` and assert on it.
- **Lazy optional imports** for `PyQt6`/`pyautogui`/`pynput`, tagged `# noqa: PLC0415`, failing soft to advisory-only.
- **Language split:** Python code, docstrings, and `logging` messages are **English** (`%`-style lazy formatting, never f-strings in log calls); **user-facing UI strings are Italian**.
- **Design doc is the spec.** `EU4_ASSISTANT_BOT_DESIGN.md` is authoritative; code comments reference its sections (e.g. `design §8.5`, `§5.3`). Docstrings carry milestone tags (`M1`–`M10`); preserve/extend them.
