# Testing Patterns

**Analysis Date:** 2026-06-23

## Test Framework

**Runner:**
- `pytest` (`>=7.0`, declared in the `dev` optional-dependency group, `pyproject.toml:40`)
- Config: `[tool.pytest.ini_options]` in `pyproject.toml:57`
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  pythonpath = ["."]
  ```
  `pythonpath = ["."]` lets tests `import eu4_assistant_bot` without an installed wheel. There is **no** `pytest.ini`, `tox.ini`, `setup.cfg`, or coverage config — pytest config lives entirely in `pyproject.toml`.

**Assertion library:**
- Plain `assert` statements (pytest rewriting). No `unittest`.
- `pytest.approx(...)` for all float comparisons (e.g. `test_parser.py:18`, `test_extractor.py:54`).
- `pytest.raises(Exc, match="regex")` for error-path tests (e.g. `test_save_unzipper.py:23`, `test_save_adapter.py:39`).

**Run commands:**
```bash
# Run the full suite (offscreen Qt is REQUIRED — UI tests construct QApplication)
QT_QPA_PLATFORM=offscreen python -m pytest -q

# Run a single file
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_decision_engine.py -q

# Run a single test or class
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_ui.py::TestMainWindow -q

# Verbose
QT_QPA_PLATFORM=offscreen python -m pytest -v
```
> On this machine the interpreter is not on `PATH` as `python`; use the venv directly: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q`. (Note: `.venv` is Python 3.14 locally, but CI runs 3.11/3.12.)

Current status: **132 passed, 1 warning** (the warning is the intentional `DeprecationWarning` from `test_parser.py::test_legacy_alias_still_works`). Full run takes ~40s, dominated by the real-time `test_watcher.py` timing tests.

## Test File Organization

**Location:** Separate top-level `tests/` directory (not co-located with source). 13 `test_*.py` files + `conftest.py` + a `fixtures/` data directory.

**Naming:** `tests/test_<module>.py` mirrors `eu4_assistant_bot/<module>.py` one-to-one.

**Coverage map (132 tests):**

| Test file | Tests | Covers (`eu4_assistant_bot/...`) | Notable focus |
|-----------|------:|----------------------------------|---------------|
| `tests/test_parser.py` | 24 | `parser.py` | Clausewitz scalars/blocks/lists, repeated keys, comments, non-ASCII, anonymous block lists, `EU4RulesLoader` mod-override merge, legacy alias deprecation |
| `tests/test_decision_engine.py` | 23 | `decision_engine.py` | Risk evaluation, reason codes, configurable thresholds, M6 military, M7 colonial + advanced-economy heuristics, action-plan mapping |
| `tests/test_ui.py` | 13 | `ui/main_window.py`, `ui/dashboard_panel.py`, `ui/advisor_panel.py`, `ui/log_panel.py` | Panel rendering, alert badge styling, log filtering, mode label, execute-request flow |
| `tests/test_extractor.py` | 12 | `extractor.py` | Parse-tree → `GameSnapshot`, manpower ×1000 scaling, single-vs-list army handling, safe defaults on empty tree |
| `tests/test_executor.py` | 9 | `executor.py` | `simulate()` (ASSIST skip / SEMI exec) and M8 `execute()` (advisory vs paused, pyautogui-optional) |
| `tests/test_mod_builder.py` | 9 | `mod/mod_builder.py` | File generation, idempotency (INSTALLED/UPDATED/SKIPPED), `.mod`/event/on_actions content |
| `tests/test_pause_controller.py` | 9 | `pause_controller.py` | Rebels/war pause triggers, anti-spam cooldown, re-trigger after clear, injected `send_key`/`on_pause` |
| `tests/test_state_reader.py` | 7 | `state_reader.py` | JSON snapshot load, null-section tolerance, M4 fields, M9 trade-node/province round-trip |
| `tests/test_save_adapter.py` | 6 | `save_adapter.py` | `key=value` extract parsing, default-on-empty, invalid-number raises |
| `tests/test_save_unzipper.py` | 6 | `save_unzipper.py` | ZIP vs plain-text saves, missing/corrupt file errors, gamestate-over-meta preference |
| `tests/test_bootstrap.py` | 5 | `main.py` (`run`) | End-to-end CLI: events.jsonl schema, JSON/save-extract/fallback sources, RiskCode string serialization |
| `tests/test_watcher.py` | 5 | `watcher.py` | watchdog file-change detection, debounce, GAME_PAUSED emission, ignore-unrelated, idempotent stop |
| `tests/test_config.py` | 4 | `config.py` | Absolute `data_dir`, `Path.home()` evaluation, SAFE/AGGRESSIVE preset wiring |

## Test Structure

**Two coexisting styles** (both accepted):

1. **Bare module-level functions** — used by most pure-logic suites (`test_parser.py`, `test_extractor.py`, `test_save_*`, `test_bootstrap.py`):
   ```python
   def test_extract_military():                 # test_extractor.py:63
       snap = StateExtractor().extract(FULL_TREE)
       assert snap.military.force_limit == 30
       assert snap.military.manpower == 22000
   ```

2. **`class Test*:` grouping** — used to group related behaviour, especially for stateful components and UI (`test_pause_controller.py`, `test_ui.py`):
   ```python
   class TestPauseControllerWar:                # test_pause_controller.py:52
       def test_pause_on_new_war(self) -> None:
           keys: list[str] = []
           ctrl = PauseController(send_key=keys.append)
           ctrl.check(_snap(active_wars=0))         # baseline
           result = ctrl.check(_snap(active_wars=1)) # new war
           assert result.reason == PauseReason.WAR_DECLARED
           assert keys == ["F1"]
   ```
   Test classes contain **no `setUp`/`__init__`** — objects are constructed inline in each test.

**Conventions:**
- **Arrange/Act/Assert** with a single blank line between phases (`out = ...` then assertions).
- Test functions are typed `-> None` in the newer suites (`test_config.py`, `test_executor.py`, `test_ui.py`); older suites omit it. Either is fine; match the file you edit.
- One behaviour per test, descriptive `test_<behaviour>` names. Edge-case tests carry a one-line docstring explaining the scenario and often reference the bug class (e.g. `"Regression test for P1 bug: null ... sections must not raise TypeError"`, `test_state_reader.py:35`).
- Test module docstrings are short and milestone-tagged: `"""Tests for ActionExecutor — simulate() (M1-M7) and execute() (M8)."""`.

## Fixtures and Factories

**Shared pytest fixtures** live in `tests/conftest.py`:
- `sample_save_zip(tmp_path)` — writes a valid `.eu4` ZIP with `meta`/`gamestate`/`ai` entries (`conftest.py:8`). Used by `test_save_unzipper.py`.
- `fixtures_dir()` — returns `tests/fixtures/` (`conftest.py:19`). Used by `test_parser.py`.

**Static fixture files** in `tests/fixtures/`:
- `sample_flat.eu4.txt` and `sample_nested.eu4.txt` — Clausewitz-format samples consumed by `ClausewitzTextParser.parse_file` tests.

**Built-in pytest fixtures heavily used:**
- `tmp_path` — every filesystem test writes into `tmp_path` (no writes to the repo or real home).
- `monkeypatch` — used to (a) sandbox `Path.home()` so config/bootstrap never touch the real home dir, and (b) `monkeypatch.chdir(tmp_path)`:
  ```python
  monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))   # test_bootstrap.py:12, test_config.py:18
  ```

**Hand-rolled factory helpers** (module-private, prefixed `_`) build domain objects with sensible defaults so each test overrides only what it cares about:
- `_snap(rebels=0.0, active_wars=0)` in `test_pause_controller.py:8`
- `_snap()`, `_recs()`, `_alerts(...)` in `test_ui.py:40-66`
- `_make_plan(action_type=...)` in `test_executor.py:50`
- `FULL_TREE` module-level dict literal in `test_extractor.py:7` as a reusable parse-tree fixture

There is **no** `factory_boy`/`faker`; factories are plain functions returning dataclasses, leveraging `GameSnapshot.empty("FRA")` as the base.

## Mocking

**No `unittest.mock` / `pytest-mock` is used anywhere.** The codebase is designed for **dependency injection** instead of patching:

- **Injected callables capture side effects.** `PauseController(send_key=keys.append, on_pause=events.append)` — the test passes a list's `.append` method and asserts on the collected list (`test_pause_controller.py:19,90`). This is the dominant "mock" pattern. Prefer it for new code (expose side-effecting deps as constructor params).

- **Qt offscreen platform** is the standard way to test PyQt6 widgets headlessly. Set **before** importing PyQt6, and provide a session-scoped `QApplication`:
  ```python
  import os
  os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")   # test_ui.py:11 (module top, before PyQt6 import)

  @pytest.fixture(scope="session")                        # test_ui.py:31
  def qapp():
      app = QApplication.instance()
      if app is None:
          app = QApplication(sys.argv)
      return app
  ```
  UI tests **call slots/handlers directly** to simulate signal delivery rather than spinning a Qt event loop: `win._on_snapshot(snap)`, `win._on_execute_requested("economy")` (`test_ui.py:147,181`). They assert on private widget attributes (`panel._lbl_country.text()`, `panel._bar_manpower.value()`).

- **`watchdog`** is exercised for real (not mocked): tests write to a `tmp_path` file and wait for the observer to fire, using tiny `debounce`/`pause_timeout` overrides and `time.sleep` (`test_watcher.py:15,56`). `FileWatcher.__init__` exposes `debounce`, `pause_timeout`, and `_poll_interval` parameters specifically so tests can shrink real timings.

- **`pyautogui`** is treated as optionally absent: `test_executor.py` asserts on a **set of acceptable statuses** because the key-send may or may not succeed in CI — `assert out[0].status in ("executed", "executed_no_pause")` (`test_executor.py:75`). The production code (`executor.py:132`) already degrades gracefully when pyautogui is missing, so no patching is needed.

**What to mock / inject:** OS keypresses, callbacks, and any external side effect → pass as a constructor/argument callable.
**What NOT to mock:** the parser, extractor, decision engine, config, file I/O against `tmp_path`, and `watchdog` — these run for real.

## Test Types

- **Unit tests** (the majority): pure-logic suites for `parser`, `extractor`, `decision_engine`, `config`, `save_adapter`, `state_reader`, `mod_builder`, `pause_controller`. Fast, no external services.
- **Integration tests:** `test_bootstrap.py` drives the full `main.run(...)` CLI pipeline (config → rules load → snapshot read → decision engine → executor → `events.jsonl`) and asserts on the emitted JSON-lines event schema.
- **UI tests:** `test_ui.py` constructs real PyQt6 widgets in offscreen mode (component-level, not E2E).
- **Concurrency/timing tests:** `test_watcher.py` runs the real `watchdog` observer + background pause-monitor thread.
- **E2E (real game interaction):** None — game keypresses and live save-watching are not exercised against EU4.

## Common Patterns

**Float assertions:**
```python
assert snap.economy.treasury == pytest.approx(230.0)     # test_extractor.py:59
assert result["treasury"] == pytest.approx(120.5)        # test_parser.py:18
```

**Error testing (message-matched):**
```python
with pytest.raises(SaveFormatError, match="not found"):
    SaveUnzipper().extract_gamestate(tmp_path / "missing.eu4")   # test_save_unzipper.py:23

with pytest.raises(SaveAdapterError, match="missing required field 'timestamp'"):
    SaveSnapshotAdapter().read_save_extract(save)                # test_save_adapter.py:39
```

**JSON-lines event assertion (integration):**
```python
event_payload = json.loads(events.read_text().splitlines()[-1])   # test_bootstrap.py:39
assert event_payload["payload"]["snapshot_source"] == "json"
```

**Round-trip serialization (`save()` → `read_json_snapshot()`):**
```python
snap.save(path)                                          # test_state_reader.py:99
restored = SnapshotReader().read_json_snapshot(path)
assert all(isinstance(n, TradeNodeState) for n in restored.trade_nodes)
```

**State-machine sequencing** (call the object repeatedly, assert accumulated side effects):
```python
ctrl.check(_snap(rebels=0.80))    # fires
ctrl.check(_snap(rebels=0.20))    # clears
result = ctrl.check(_snap(rebels=0.80))   # fires again
assert keys == ["F1", "F1"]               # test_pause_controller.py:41
```

## Coverage Gaps

No coverage tooling is configured (`coverage`/`pytest-cov` are not dependencies), so there are no enforced thresholds. Notable untested areas to be aware of when planning work:

- **`main.run_with_ui()`** (`main.py:151`) — the live `FileWatcher → DecisionEngine → MainWindow` UI pipeline, including `_process_save` and `_watcher_loop`, has **no test** (only the non-UI `run()` is covered by `test_bootstrap.py`). Note `_process_save` calls `ClausewitzTextParser().parse(...)` but the parser's method is `parse_text(...)` — this path is unexercised and looks like a latent bug.
- **`executor.execute()` real-pause branch** — the `paused == True` path (pyautogui actually sending Space) is never asserted true; tests accept either outcome.
- **`telemetry.setup_logging` / `emit_event`** — no direct unit tests; only indirectly exercised via `test_bootstrap.py` writing `events.jsonl`. The `emit_event` failure branch (`telemetry.py:46`) is marked `# pragma: no cover`.
- **`pause_controller._default_send_key`** — the real xdotool/pynput key sender is never invoked in tests (always overridden via `send_key=`).
- **`extractor` advanced extraction** — `_extract_trade_nodes` and `_extract_provinces` (`extractor.py:228,258`) have no dedicated extractor tests; trade-node/province coverage exists only at the `state_reader` round-trip level.
- **UI hotkey** (`ui/hotkey.py`) — no test file.
- **CLI arg parsing** (`main.parse_args`, `main.main`) — not directly tested.

## CI

`.github/workflows/ci.yml` runs the suite on **`ubuntu-latest`** across a **Python 3.11 and 3.12 matrix** (`ci.yml:13`). It installs PyQt6 system libs (`libgl1`, `libegl1`, `libglib2.0-0`, `libdbus-1-3`), `pip install -e ".[dev]"`, then runs `python -m pytest -q` with `QT_QPA_PLATFORM: offscreen` exported as a job env var (`ci.yml:35`). A separate `.github/workflows/build.yml` handles packaging. Match the 3.11/3.12 target when using language features — do not rely on 3.13+/3.14 syntax even though the local `.venv` is 3.14.

---

*Testing analysis: 2026-06-23*
