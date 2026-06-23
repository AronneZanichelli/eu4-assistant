# Technology Stack

**Analysis Date:** 2026-06-23

## Languages

**Primary:**
- Python 3.11+ - Entire application (`eu4_assistant_bot/` package, `tests/`). Source uses `from __future__ import annotations` and 3.10+ syntax (`X | None`, `match`-free but PEP 604 unions, `@dataclass(slots=True)`).

**Secondary:**
- Clausewitz script (Paradox text format) - Generated, not authored Python. Emitted as `.mod`/`.txt` templates in `eu4_assistant_bot/mod/mod_builder.py` (`_MOD_FILE_TEMPLATE`, `_EVENT_FILE`, `_ON_ACTIONS_FILE`). Also *parsed* (read-only) by `eu4_assistant_bot/parser.py`.

## Runtime

**Environment:**
- CPython 3.11 / 3.12 - declared support. `pyproject.toml` sets `requires-python = ">=3.11"`; classifiers list 3.11 and 3.12; CI matrix runs 3.11 and 3.12.
- Local `.venv` was created with Python 3.14.4 (`.venv/pyvenv.cfg`) — newer than the declared support floor; treat the 3.11/3.12 matrix as authoritative for compatibility.
- Threading model: standard-library threading. `FileWatcher` runs a `watchdog` observer thread plus a daemon pause-monitor thread (`eu4_assistant_bot/watcher.py`); `run_with_ui()` runs the watcher loop in a daemon thread named `eu4-watcher` (`eu4_assistant_bot/main.py:242`) while PyQt6 owns the main thread.

**Package Manager:**
- pip - install via `pip install -e ".[dev]"` / `".[ui]"` / `".[bot]"` (`README.md`).
- Lockfile: missing - no `requirements.txt`, `poetry.lock`, `Pipfile.lock`, or `uv.lock`. Versions are pinned only as ranges in `pyproject.toml`.

## Frameworks

**Core:**
- PyQt6 `>=6.5,<7.0` - Desktop GUI (3-column window: dashboard / advisor / log). Entry `eu4_assistant_bot/ui/main_window.py` (`QMainWindow`), panels in `eu4_assistant_bot/ui/`. Optional extra (`ui`, `bot`, `dev`); not a base dependency.

**Testing:**
- pytest `>=7.0` - Test runner. Config in `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`). 14 test modules in `tests/`. No assertion library beyond `assert`; no pytest plugins declared.

**Build/Dev:**
- setuptools `>=61` - Build backend (`[build-system]` in `pyproject.toml`, `build-backend = "setuptools.build_meta"`). Package discovery via `[tool.setuptools.packages.find]` (`include = ["eu4_assistant_bot*"]`).
- PyInstaller `>=5.0,<7.0` - Windows standalone `.exe` packaging. Spec at `eu4_assistant.spec`. Optional extra (`pkg`).

## Key Dependencies

**Critical (base — always installed):**
- watchdog `>=4.0,<7.0` - Filesystem event monitoring of the EU4 autosave file. Used in `eu4_assistant_bot/watcher.py` (`watchdog.observers.Observer`, `watchdog.events.FileSystemEventHandler`). This is the only non-optional runtime dependency.

**Optional — UI / automation:**
- PyQt6 `>=6.5,<7.0` - GUI (extras: `ui`, `bot`, `dev`).
- pynput `>=1.7,<2.0` - Global hotkey listener (F2 show/hide, `eu4_assistant_bot/ui/hotkey.py`) and keyboard fallback for the pause controller on Windows/macOS (`eu4_assistant_bot/pause_controller.py`). Extras: `ui`, `bot`, `dev`.
- pyautogui `>=0.9,<1.0` - Sends keystrokes to EU4 for real action execution (Space = pause toggle, `eu4_assistant_bot/executor.py:_pause_game`). Extra: `bot` only.

**Build-only:**
- pyinstaller `>=5.0,<7.0` - Extra: `pkg`.

**Standard library (no third-party needed):**
- `zipfile` - decompress `.eu4` ZIP saves (`save_unzipper.py`).
- `json` - snapshot read/write + JSONL telemetry (`state_reader.py`, `models.py`, `telemetry.py`).
- `subprocess` - invokes `xdotool` for keypress on Linux (`pause_controller.py`).
- `argparse`, `logging`, `logging.handlers`, `threading`, `queue`, `re`, `pathlib`, `dataclasses`, `enum`.

## Optional-Dependency Groups

Defined under `[project.optional-dependencies]` in `pyproject.toml` (verified against `eu4_assistant_bot.egg-info/requires.txt`):

| Extra | Packages | Purpose |
|-------|----------|---------|
| `ui` | `PyQt6>=6.5,<7.0`, `pynput>=1.7,<2.0` | Advisor + dashboard + log GUI, F2 global hotkey. No game keystroke automation. |
| `bot` | `PyQt6>=6.5,<7.0`, `pynput>=1.7,<2.0`, `pyautogui>=0.9,<1.0` | UI + real action execution (semi-bot / full-bot) via pyautogui keystrokes. |
| `dev` | `pytest>=7.0`, `PyQt6>=6.5,<7.0`, `pynput>=1.7,<2.0` | Test + headless UI testing. (No pyautogui — execution path is mocked/skipped in tests.) |
| `pkg` | `pyinstaller>=5.0,<7.0` | Build the Windows `.exe`. Typically combined: `pip install -e ".[bot,pkg]"`. |

Note: base install (no extra) yields a CLI that can run `--mode assist` analysis from a JSON/save-extract snapshot but cannot launch the GUI or watch files-via-UI (PyQt6 absent). `eu4_assistant_bot/executor.py` and `pause_controller.py` degrade gracefully when `pyautogui`/`pynput` are missing (caught `ImportError`, advisory-only fallback).

## Configuration

**Application config:**
- No config file format. Configuration is code-driven via `eu4_assistant_bot/config.py` (`AppConfig`, `build_config()`), populated from CLI flags in `eu4_assistant_bot/main.py` (`parse_args()`).
- Default paths resolved at runtime from `Path.home()`:
  - EU4 install: `~/Games/Europa Universalis IV`
  - EU4 documents: `~/Documents/Paradox Interactive/Europa Universalis IV`
  - Active mods manifest: `.../Europa Universalis IV/dlc_load.json`
  - App data dir: `~/.eu4-assistant` (holds `logs/`, `snapshots/`, `events.jsonl`).
- GUI window geometry persisted via `QSettings("EU4Assistant", "MainWindow")` (`eu4_assistant_bot/ui/main_window.py:112`) — Windows registry / platform-native settings store, not a project file.
- No `.env` file is present and no environment variables are read by the application code (`QT_QPA_PLATFORM=offscreen` is set only in CI for headless tests).

**Build config:**
- `pyproject.toml` - project metadata, deps, extras, scripts, pytest config.
- `eu4_assistant.spec` - PyInstaller build (windowed/no-console, `excludes=['tkinter','matplotlib','numpy']`, `hiddenimports` for PyQt6 + watchdog + internal subpackages, UPX enabled).
- `.gitignore` - ignores build artifacts plus `*.eu4`, `events.jsonl`, `*.log`, `.eu4-assistant/`.

## Platform Requirements

**Development:**
- Any OS for tests. CI runs on `ubuntu-latest` with headless Qt (`QT_QPA_PLATFORM=offscreen`) and system libs `libgl1 libegl1 libglib2.0-0 libdbus-1-3` for PyQt6 (`.github/workflows/ci.yml`).
- Linux runtime pause path additionally requires the external `xdotool` binary (not pip-installable; `pause_controller.py` warns and no-ops if absent).

**Production:**
- Windows (primary). `pyproject.toml` classifier: `Operating System :: Microsoft :: Windows`; README states Windows required to run alongside EU4. Build artifact `dist/eu4-assistant.exe` produced on `windows-latest` for `v*` tags (`.github/workflows/build.yml`).

## Build & CI

**CI (`.github/workflows/ci.yml`):**
- Trigger: push to any branch, PRs to `main`.
- Matrix: Python 3.11 + 3.12 on `ubuntu-latest`.
- Steps: install PyQt6 system libs → `pip install -e ".[dev]"` → `python -m pytest -q` with `QT_QPA_PLATFORM=offscreen`.

**Release build (`.github/workflows/build.yml`):**
- Trigger: tags matching `v*`.
- Runs on `windows-latest`, Python 3.11: `pip install -e ".[bot,pkg]"` → `pyinstaller eu4_assistant.spec --clean` → uploads `dist/eu4-assistant.exe` as artifact.

## Entry Points

- Console script: `eu4-assistant = "eu4_assistant_bot.main:main"` (`[project.scripts]`).
- Module form: `python -m eu4_assistant_bot` → `eu4_assistant_bot/__main__.py` → `main.main()`.
- PyInstaller target: `eu4_assistant_bot/main.py` → `dist/eu4-assistant.exe`.
- Two runtime modes inside `main.py`:
  - `run()` - one-shot analysis from `--snapshot-json` or `--snapshot-save`, emits a `startup` event.
  - `run_with_ui()` - launches PyQt6 window + live `FileWatcher` pipeline when `--watch SAVE_PATH` is given.

---

*Stack analysis: 2026-06-23*
