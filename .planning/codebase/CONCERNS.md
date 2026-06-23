# Codebase Concerns

**Analysis Date:** 2026-06-23

**Project stage:** Alpha (`v0.5.0`, last release 2026-03-17 per `CHANGELOG.md` — ~3 months stale at analysis time).

This document inventories technical debt, latent bugs, fragile areas, safety/security concerns, platform coupling, dependency staleness and test-coverage gaps. Each entry carries a severity (high / med / low), a file location, and a suggested action.

---

## Known Bugs

### Live UI pipeline calls a non-existent parser method (`parse` vs `parse_text`)

- **Severity:** HIGH
- **Symptoms:** The flagship "watch a live save" feature (`--watch`) never produces a snapshot. On the first save event the call raises `AttributeError: 'ClausewitzTextParser' object has no attribute 'parse'`, which is caught by the broad handler below and surfaced to the user as a generic `"Errore parsing save: ..."` log line. No dashboard/advisor data ever appears.
- **Files:** `eu4_assistant_bot/main.py:201` calls `ClausewitzTextParser().parse(gamestate_text)`, but the parser only defines `parse_text(text)` and `parse_file(path)` (`eu4_assistant_bot/parser.py:182`, `:191`). Confirmed via grep: `.parse(` appears only at `main.py:201`; every test uses `.parse_text(`.
- **Trigger:** Run `eu4-assistant --watch <path-to>.eu4` (SEMI/FULL/ASSIST, any mode) and let any save write occur.
- **Workaround:** None for end users. The CLI `run()` path (non-UI) is unaffected because it does not call the recursive parser at all.
- **Fix approach:** Change `main.py:201` to `ClausewitzTextParser().parse_text(gamestate_text)`. Add a regression test that drives `_process_save` end-to-end with a real ZIP/plain `.eu4` fixture (see Test Coverage Gaps below) so this class of error cannot recur.

### Overly broad `except (SaveFormatError, Exception)` masks programming errors

- **Severity:** HIGH (it is what hides the bug above)
- **Symptoms:** Any error in the save-processing path — including `AttributeError`, `TypeError`, `KeyError` from the extractor, or genuine I/O failures — is collapsed into one warning and a UI log line, then silently dropped. Catching `Exception` makes the preceding `SaveFormatError` redundant.
- **Files:** `eu4_assistant_bot/main.py:203` (`except (SaveFormatError, Exception) as exc:`).
- **Trigger:** Any exception inside `_process_save`.
- **Workaround:** None.
- **Fix approach:** Narrow to the expected domain error (`SaveFormatError`) for the "bad save" message, and let unexpected exceptions either propagate or be logged with `logger.exception(...)` and a distinct "internal error" log level so real bugs are visible during development.

### Duplicate key in `_ACTION_DESCRIPTIONS` (silent dict overwrite)

- **Severity:** LOW
- **Symptoms:** `military_recover_manpower` is defined twice in the same dict literal; the second value silently overrides the first. Harmless today (both values are near-synonyms) but it is a copy-paste smell and a lint failure waiting to happen.
- **Files:** `eu4_assistant_bot/executor.py:24` and `eu4_assistant_bot/executor.py:30`.
- **Trigger:** N/A (static).
- **Workaround:** N/A.
- **Fix approach:** Delete the duplicate entry. Enable a linter rule (`F601`/`ruff`) to catch duplicate literal keys.

### `PauseController` sends `F1`, which is not the EU4 pause key

- **Severity:** MED
- **Symptoms:** On a critical event (rebels imminent / new war) the controller presses `F1` to "pause the game" (`pause_controller.py:73`, docstring at `:7`). In EU4, pause is toggled by **Space** (the same key `ActionExecutor._pause_game()` correctly uses at `executor.py:141`); `F1` is bound to interface/ledger actions. The two pause mechanisms in the codebase disagree, so the auto-pause-on-risk feature likely does not pause the game and may open an unintended panel.
- **Files:** `eu4_assistant_bot/pause_controller.py:73` (`self._send_key("F1")`), `eu4_assistant_bot/executor.py:141` (`pyautogui.press("space")`).
- **Trigger:** Snapshot crossing `rebels_threshold` or `active_wars` increasing while in a mode that runs the controller.
- **Workaround:** None.
- **Fix approach:** Decide on one pause key (Space) and one send-key backend (see fragile-area note on the dual xdotool/pynput/pyautogui split), then unify `PauseController` and `ActionExecutor` to use it. Add a test asserting the key sent equals the configured pause key.

---

## Tech Debt

### Legacy parser kept behind a deprecated callable alias

- **Severity:** LOW
- **Issue:** `ClausewitzParser(...)` is a deprecated factory that emits a `DeprecationWarning` and returns `_LegacyClausewitzParser` (a flat regex M1 PoC parser). It exists only for backward compatibility and is still the engine behind `EU4RulesLoader` (which uses the *new* `ClausewitzTextParser`, but the legacy class lingers in the module).
- **Files:** `eu4_assistant_bot/parser.py:234-241` (alias), `eu4_assistant_bot/parser.py:205-231` (`_LegacyClausewitzParser`), test pins it at `tests/test_parser.py:153` (`test_legacy_alias_still_works`).
- **Impact:** Dead-weight code path that must keep passing tests; risk of someone instantiating the weak flat parser by mistake.
- **Fix approach:** Confirm no internal caller uses `ClausewitzParser`/`_LegacyClausewitzParser` (grep shows none outside the parser module and its test). Schedule removal for the next minor bump, or convert the alias into a hard error after a deprecation window.

### Legacy `key=value` save adapter (M1/M2 bridge format)

- **Severity:** LOW
- **Issue:** `SaveSnapshotAdapter` parses a hand-written `key=value` extract that captures only economy/military/risk; war, diplomacy, tech, ideas, trade nodes and provinces default to empty. The code itself flags this as a legacy bridge superseded by `SaveUnzipper` + `StateExtractor`.
- **Files:** `eu4_assistant_bot/save_adapter.py:61-64` (explicit note), whole file `save_adapter.py`. Reached via `main.py:57` (`--snapshot-save`).
- **Impact:** Snapshots produced this way are structurally incomplete; recommendations derived from them silently ignore most of the game state.
- **Fix approach:** Keep for tests/demos but mark the `--snapshot-save` CLI flag as deprecated in help text, and document that real analysis requires the live/`.eu4` path. Remove once the live path (above bug) is fixed and proven.

### Two parallel snapshot input formats with overlapping responsibility

- **Severity:** LOW
- **Issue:** `SnapshotReader` (JSON) and `SaveSnapshotAdapter` (key=value) both build a `GameSnapshot` from text, with near-identical defensive coercion helpers (`_to_float`/`_to_int` vs the extractor's `_float`/`_int`). Three coercion implementations now exist (`save_adapter.py`, `extractor.py`, implicitly `state_reader.py`).
- **Files:** `eu4_assistant_bot/save_adapter.py:84-104`, `eu4_assistant_bot/extractor.py:299-321`, `eu4_assistant_bot/state_reader.py`.
- **Impact:** Divergent null/empty handling between code paths; maintenance drift.
- **Fix approach:** Extract a single shared coercion module and have all three consumers use it.

### `M`-milestone comments scattered through production code

- **Severity:** LOW
- **Issue:** Many comments/constants are tagged with internal milestone labels (`M1`–`M10`) that mean nothing to a new reader (e.g. `decision_engine.py:21` "M6:", `executor.py:1` "simulated (M1-M7) and real (M8+)").
- **Files:** widespread — `eu4_assistant_bot/decision_engine.py`, `executor.py`, `extractor.py`, `models.py`, `state_reader.py`.
- **Impact:** Documentation noise; couples code comments to a private roadmap.
- **Fix approach:** Replace milestone references with behavioural descriptions during normal edits (do not do a sweeping refactor solely for this).

---

## Security & Safety Considerations

### OS automation sends real keystrokes to a running game with no failsafe

- **Severity:** HIGH
- **Risk:** In SEMI_BOT/FULL_BOT the app injects synthetic key events (`Space`, `F1`, `F2`) into the foreground window via `pyautogui`/`pynput`/`xdotool`. There is no window-focus check (keystrokes go wherever focus happens to be — could be the user's browser, terminal, or another game), no `pyautogui.FAILSAFE`/`PAUSE` configuration, and no rate limiting. A misfire types into the wrong application.
- **Files:** `eu4_assistant_bot/executor.py:125-146` (`_pause_game`), `eu4_assistant_bot/pause_controller.py:110-131` (`_default_send_key`). Grep confirms no `FAILSAFE`/`PAUSE`/focus-guard anywhere in `eu4_assistant_bot/`.
- **Current mitigation:** SEMI_BOT shows a confirmation dialog before executing (`main_window.py:172`); graceful no-op if `pyautogui` is missing.
- **Recommendations:** (1) Verify the EU4 window is focused before sending any key (e.g. active-window title check). (2) Explicitly set `pyautogui.FAILSAFE = True` and a small `pyautogui.PAUSE`. (3) Keep all sends behind an explicit kill-switch/hotkey the user can hold to abort.

### FULL_BOT executes without a confirmation dialog

- **Severity:** HIGH
- **Risk:** The confirmation dialog in the UI is gated on `self._mode == BotMode.SEMI_BOT` only. In FULL_BOT the code skips straight to `self._executor.execute(...)`, which sends keystrokes to the game. Although the M8 executor currently only sends a pause, the design intent (per `executor.py:84` and `CHANGELOG` M8) is "FULL_BOT = direct execute", so this gap becomes dangerous the moment real menu navigation lands.
- **Files:** `eu4_assistant_bot/ui/main_window.py:170-182` (only SEMI_BOT branches into `QMessageBox.question`; FULL_BOT falls through), `eu4_assistant_bot/executor.py:108` ("SEMI_BOT / FULL_BOT: interact with game").
- **Current mitigation:** None for FULL_BOT.
- **Recommendations:** Require an explicit, separate opt-in for FULL_BOT (e.g. a persisted "I understand" acknowledgement) and/or keep a confirmation/undo affordance. Treat `ActionPlan.requires_confirmation=True` (set for every plan at `decision_engine.py:443`) as authoritative in `execute()`, not only in `simulate()`.

### `ActionPlan.requires_confirmation` is honoured in `simulate()` but ignored in `execute()`

- **Severity:** MED
- **Risk:** `simulate()` skips plans needing confirmation in ASSIST mode (`executor.py:52`). `execute()` never inspects `requires_confirmation` at all — confirmation is enforced (partially) only by the UI layer, so any non-UI caller of `execute()` bypasses the safety flag entirely.
- **Files:** `eu4_assistant_bot/executor.py:77-123`.
- **Current mitigation:** UI dialog (SEMI_BOT only).
- **Recommendations:** Enforce `requires_confirmation` inside `execute()` (or require a `confirmed=True` argument) so the safety contract does not depend on the caller.

### Global hotkey listener captures system-wide key events

- **Severity:** MED
- **Risk:** `HotkeyManager` installs a global `pynput` keyboard listener (`ui/hotkey.py:38`) that observes every keypress system-wide to detect `F2`. This is a keylogger-shaped capability; on some OSes it requires accessibility/input-monitoring permissions and can be flagged by anti-cheat/security tooling. The callback runs on the listener thread and only swallows exceptions (`ui/hotkey.py:49-54`).
- **Files:** `eu4_assistant_bot/ui/hotkey.py` (whole file).
- **Current mitigation:** Listener is daemonised; exceptions are logged.
- **Recommendations:** Document the OS permission requirement; scope listening as narrowly as the library allows; ensure the listener is always stopped on shutdown (it is created but `HotkeyManager` is not wired into `run_with_ui` — see Test/Wiring gap). Warn users that injecting keys into an online game may violate EU4/anti-cheat terms.

### Subprocess invocation of `xdotool` on Linux

- **Severity:** LOW
- **Risk:** `pause_controller._default_send_key` shells out to `xdotool key <key>` (`pause_controller.py:114-119`). The `key` argument is internal (`"F1"`), so there is no untrusted input today, but it relies on an external binary that is frequently absent and is X11-only (fails silently under Wayland).
- **Files:** `eu4_assistant_bot/pause_controller.py:110-131`.
- **Current mitigation:** `FileNotFoundError`/`SubprocessError` caught and logged; 3s timeout.
- **Recommendations:** Prefer a single Python-level backend (`pynput`) across platforms; if keeping `xdotool`, detect Wayland and warn.

---

## Fragile Areas

### Recursive Clausewitz text parser robustness

- **Severity:** MED
- **Files:** `eu4_assistant_bot/parser.py:63-189` (`_tokenize`, `_parse_block`, `ClausewitzTextParser`).
- **Why fragile:**
  - **Unbounded recursion:** `_parse_block` recurses per nested block with no depth limit. Real EU4 `gamestate` files are tens of MB with deep nesting; a pathological/corrupt file can hit Python's recursion limit and raise `RecursionError`, which (in the live path) is currently swallowed (`main.py:203`).
  - **Whole file tokenised into a Python list:** `_tokenize` builds one list holding every token of a multi-MB save before parsing — high memory, no streaming.
  - **Malformed input is silently skipped:** bare tokens without `=` are dropped (`parser.py:168-170`), and the parser appends a synthetic `}` sentinel (`parser.py:187`); a truncated save can produce a partial dict with no error signalled.
  - **Quote handling assumes no escaped quotes** (documented at `parser.py:88-90`) — a future/modded format with `\"` would mis-tokenise.
- **Safe modification:** Add a recursion-depth guard and a maximum-token/size guard; consider an iterative parser or a vetted library for the real save path. Add fuzz/large-file fixtures.
- **Test coverage:** Good for *small* well-formed snippets (`tests/test_parser.py`, 24 tests) but **no** large-file, deeply-nested, truncated, or adversarial-input tests.

### `pyautogui` blind keystroke automation in `executor.py`

- **Severity:** MED (overlaps the safety entry above; called out separately as a robustness concern)
- **Files:** `eu4_assistant_bot/executor.py:125-146`.
- **Why fragile:** Imports `pyautogui` lazily inside `_pause_game` and presses keys with no verification that EU4 received them, no focus check, and a blanket `except Exception` that downgrades any failure to advisory. The success/failure of a real game action is inferred purely from "did `press()` raise", not from observed game state.
- **Safe modification:** Gate on window focus; surface failures distinctly; never claim `status="executed"` without evidence of effect.
- **Test coverage:** `tests/test_executor.py` (9 tests) exercises only `simulate()` and the mode branching of `execute()`; the actual `pyautogui` send path is not tested (and cannot be on headless CI without mocking).

### File-watcher debounce / pause-monitor races

- **Severity:** MED
- **Files:** `eu4_assistant_bot/watcher.py` (whole file), consumed by `main.py:224-243`.
- **Why fragile:**
  - **Debounce timer fires on a `threading.Timer` thread** while `_schedule` may cancel/replace it from the watchdog thread. The lock protects timer swap, but a timer can still fire its `_fire` callback after `stop()` has nominally torn things down (the observer is stopped but an in-flight debounce timer is daemonised and not joined — `watcher.py:64-75`, `:142-152`).
  - **Pause-monitor granularity:** the monitor sleeps in `_poll_interval` (default 10s) chunks (`watcher.py:170-183`); `stop()` waits up to `poll_interval + 1`s, so shutdown can block ~11s.
  - **Watches the parent directory** (`recursive=False`) and filters by resolved path (`watcher.py:54-59`, `:133`). EU4 typically writes a temp file then renames it over the autosave; a rename may surface as a `moved`/`created` event on a *different* name, so `on_modified`/`on_created` filtering on the final path can miss writes depending on the OS/watchdog backend.
  - **`_running` is a plain bool** read/written across threads without a lock (it is only a stop flag, so low risk, but technically a data race).
- **Safe modification:** Join/cancel the debounce timer in `stop()`; handle `on_moved` for the atomic-rename save pattern; shorten or interrupt the pause-monitor sleep on stop (e.g. `threading.Event.wait`).
- **Test coverage:** `tests/test_watcher.py` (5 tests) covers basic emit/debounce; no rename-pattern, no shutdown-race, no GAME_PAUSED-timing tests.

### `StateExtractor` country lookup is positional and assumes single-occurrence keys

- **Severity:** MED
- **Files:** `eu4_assistant_bot/extractor.py:39-79`, `:283-288` (`_country_block`), `parser.py:51-60` (`_set_key`).
- **Why fragile:**
  - Repeated keys in a save become a Python `list` via `_set_key`. The extractor's `_country_block` assumes `tree["countries"]` is a `dict` keyed by tag; if the parser ever returns a list for `countries`/`provinces` (e.g. duplicated top-level keys), the lookup returns `{}` and the whole snapshot silently goes empty.
  - **Heuristic field semantics:** `manpower` is multiplied by 1000 (`extractor.py:111-113`), coalition risk is derived from `overextension_percentage/100` (`extractor.py:175`), rebel risk from `len(rebel_faction)*0.2` (`extractor.py:171`), idea "completed" if count `>= 7` (`extractor.py:216`). These mappings are unvalidated against real saves and are brittle to EU4 patch changes.
  - **`_extract_diplomacy` computes `truce_raw`/`alliances` but `active_wars` comes from `num_of_war_with_us`**, and `ae_map` is hard-coded to `{}` (`extractor.py:152`) — diplomacy analysis is effectively stubbed.
- **Safe modification:** Validate against captured real `gamestate` fixtures; centralise the magic scaling constants with provenance comments; defensively handle `list`-typed `countries`/`provinces`.
- **Test coverage:** `tests/test_extractor.py` (12 tests) uses a hand-built `FULL_TREE` dict, not output from the real parser — so parser→extractor integration is untested.

### `setup_logging(..., force=True)` resets global logging config

- **Severity:** LOW
- **Files:** `eu4_assistant_bot/telemetry.py:24-38`.
- **Why fragile:** `logging.basicConfig(..., force=True)` tears down and replaces all root handlers. Calling `run()` then `run_with_ui()` (or embedding the package) clobbers any host logging setup.
- **Safe modification:** Configure a named logger/handlers idempotently instead of forcing the root config.

---

## Performance Bottlenecks

### Full-file tokenisation + full-tree materialisation per save

- **Severity:** MED
- **Problem:** Every autosave triggers: read entire gamestate into a `str`, tokenise into a full `list[str]`, build a complete nested `dict`, then walk it. For real saves (tens of MB) this is CPU- and memory-heavy and runs on the watcher thread for every monthly save.
- **Files:** `eu4_assistant_bot/parser.py:63-189`, `eu4_assistant_bot/save_unzipper.py:52-72` (`zf.read(...)` loads the whole entry), `eu4_assistant_bot/main.py:199-202`.
- **Cause:** No streaming/partial parse; the engine only needs a handful of fields but parses everything.
- **Improvement path:** Parse only the player country block / required keys, or stream-tokenise; cache the parsed tree between unchanged saves. Benchmark against a real `.eu4` before optimising.

### Province / trade-node extraction iterates the entire map

- **Severity:** LOW
- **Problem:** `_extract_provinces` loops every province in the save and filters by owner (`extractor.py:258-279`); `_extract_trade_nodes` loops all nodes and, per node, loops all participating countries (`extractor.py:228-256`). For a large game this is O(provinces + nodes×countries) every month.
- **Files:** `eu4_assistant_bot/extractor.py:228-279`.
- **Improvement path:** Acceptable for now; revisit only if profiling on real saves shows it matters.

---

## Platform Coupling

### Windows-only runtime target, cross-platform input code

- **Severity:** MED
- **Problem:** The project declares itself Windows-only (`classifiers` "Operating System :: Microsoft :: Windows" in `pyproject.toml:20`; build workflow runs `windows-latest` and produces `eu4-assistant.exe`, `.github/workflows/build.yml`). Yet input handling has Linux (`xdotool`) and macOS branches (`pause_controller.py:110-131`) that are neither the supported target nor exercised by the Windows-only release build.
- **Files:** `pyproject.toml:16-24`, `.github/workflows/build.yml:8-9`, `eu4_assistant_bot/pause_controller.py:110-131`.
- **Impact:** Untested code paths for non-shipped platforms; confusion about what is actually supported. (EU4 itself does run on Linux/macOS, so the ambiguity is real.)
- **Suggested action:** Decide whether non-Windows is supported. If not, drop the Linux/macOS send-key branches or clearly mark them experimental. If yes, add CI coverage for them.

### Input-automation dependencies fail to build on modern Linux + Python 3.14

- **Severity:** MED (blocks local dev/test on Linux with current interpreter)
- **Problem:** The `.venv` in-repo and the host interpreter are Python **3.14** (see below), but `pynput`/`pyautogui` and their transitive input backends (e.g. `evdev`) historically fail to build/import on Linux against bleeding-edge CPython. Because `pynput` is imported at module top-level in `ui/hotkey.py:10`, importing the UI on a machine where `pynput` won't install breaks the whole UI import, not just the hotkey feature.
- **Files:** `eu4_assistant_bot/ui/hotkey.py:10` (top-level `from pynput.keyboard import ...`), `pyproject.toml:30-43` (`pynput` in `ui`/`bot`/`dev` extras). Contrast `pause_controller.py:125` and `executor.py:133`, which import `pynput`/`pyautogui` lazily and degrade gracefully.
- **Impact:** Running `pip install -e ".[dev]"` then importing UI on Linux/Python 3.14 can fail at import time; CI hides this by pinning Python 3.11/3.12.
- **Suggested action:** Make the `pynput` import in `ui/hotkey.py` lazy (mirror the executor/pause-controller pattern) so the UI degrades to "no global hotkey" instead of failing to import. Pin/verify `pynput`/`pyautogui` versions that support the runtime interpreter, or constrain `requires-python` to the actually-tested range.

---

## Version & Dependency Drift

### Declared/CI Python versions (3.11–3.12) do not match the runtime interpreter (3.14)

- **Severity:** MED
- **Problem:** `pyproject.toml` advertises `requires-python = ">=3.11"` and classifiers for only 3.11/3.12 (`pyproject.toml:11`, `:21-22`); CI tests only `["3.11", "3.12"]` (`.github/workflows/ci.yml:14`) and the release build uses `3.11` (`.github/workflows/build.yml:16`). The in-repo virtual environment / dev interpreter is **Python 3.14**, so the code is being run on a version that is never tested in CI and is not listed as supported.
- **Files:** `pyproject.toml:11`, `pyproject.toml:21-22`, `.github/workflows/ci.yml:14`, `.github/workflows/build.yml:16`.
- **Impact:** Untested-on-runtime risk; classifiers misrepresent support; 3.14-specific deprecations/removals (and the `pynput`/`evdev` build issue above) go uncaught by CI.
- **Suggested action:** Add `3.13`/`3.14` to the CI matrix (or whichever the project actually runs), update classifiers, and confirm all dependencies have wheels for that interpreter.

### Upper-bound pins that already lag current major releases

- **Severity:** LOW–MED
- **Problem:** Several dependencies are capped below their current major versions, so the project will silently miss security/bug fixes and eventually fail to resolve on fresh installs:
  - `watchdog>=4.0,<7.0` (`pyproject.toml:26`)
  - `PyQt6>=6.5,<7.0` (`pyproject.toml:31`, `:35`, `:41`)
  - `pynput>=1.7,<2.0` (`pyproject.toml:32`, `:36`, `:42`)
  - `pyautogui>=0.9,<1.0` (`pyproject.toml:37`)
  - `pyinstaller>=5.0,<7.0` (`pkg`, `pyproject.toml:45`)
  - `pytest>=7.0` (no upper bound — inconsistent with the rest; could pull a future-breaking pytest, `pyproject.toml:40`)
- **Files:** `pyproject.toml:25-46`.
- **Impact:** Caps freeze the project on potentially outdated/insecure releases; the lone uncapped `pytest` is inconsistent with the project's otherwise-conservative pinning policy.
- **Suggested action:** Review each cap against the latest release; widen where the new major is known-compatible, and add a deliberate (not accidental) bound to `pytest`. Run `pip list --outdated` in the supported interpreter and record decisions.

### No dependency lockfile

- **Severity:** LOW
- **Problem:** Only `pyproject.toml` ranges exist; there is no lockfile (no `requirements.txt`, `poetry.lock`, `uv.lock`, etc.) and `.gitignore` excludes `dist/`/`build/`. CI installs unpinned latest-within-range, so a transitive update can break the build non-reproducibly.
- **Files:** repo root (`pyproject.toml` only); `.gitignore`.
- **Impact:** Non-reproducible CI/release builds.
- **Suggested action:** Generate and commit a lockfile for the supported interpreter, or pin exact versions in CI.

---

## Test Coverage Gaps

The suite is healthy in breadth (122 test functions across 14 files) but the **highest-risk runtime paths are exactly the untested ones**.

### Live UI watcher pipeline (`run_with_ui` / `_process_save` / `_watcher_loop`) — UNTESTED

- **What's not tested:** The end-to-end flow that turns a real `.eu4` file into UI updates — i.e. the feature that contains the HIGH-severity `parse()` bug. Grep confirms no test references `run_with_ui`, `_process_save`, or `_watcher_loop`.
- **Files:** `eu4_assistant_bot/main.py:151-245`.
- **Risk:** The flagship feature can be (and currently is) completely broken with a green test suite.
- **Priority:** HIGH. Add an integration test driving `_process_save` with `tests/fixtures` ZIP and plain saves through `SaveUnzipper → ClausewitzTextParser → StateExtractor`.

### Parser → Extractor integration — UNTESTED

- **What's not tested:** `StateExtractor` is only ever fed a hand-authored `FULL_TREE` dict (`tests/test_extractor.py:20-48`), never the actual output of `ClausewitzTextParser`. The seam where parser shape and extractor expectations must agree is unverified.
- **Files:** `tests/test_extractor.py`, `eu4_assistant_bot/parser.py`, `eu4_assistant_bot/extractor.py`.
- **Risk:** Shape mismatches (e.g. `list` vs `dict` for `countries`) produce silently-empty snapshots.
- **Priority:** HIGH.

### `pyautogui` / `pynput` / `xdotool` send-key paths — UNTESTED

- **What's not tested:** `ActionExecutor._pause_game` (`executor.py:125-146`) and `PauseController._default_send_key` (`pause_controller.py:110-131`). `PauseController` tests inject a fake `send_key` (`tests/test_pause_controller.py`), so the real backend selection/keypress is never exercised or even mocked.
- **Files:** `tests/test_executor.py`, `tests/test_pause_controller.py`.
- **Risk:** Wrong key (the F1-vs-Space bug), missing focus guard, and backend-selection logic all ship untested.
- **Priority:** MED. Mock the backends and assert the exact key + that failures degrade correctly.

### Global hotkey (`HotkeyManager`) — UNTESTED and not wired in

- **What's not tested:** `eu4_assistant_bot/ui/hotkey.py` has no test, and grep shows `HotkeyManager` is never instantiated by `run_with_ui` — the F2 toggle is implemented (`main_window.toggle_visibility`, tested) but the global listener that should drive it is not connected.
- **Files:** `eu4_assistant_bot/ui/hotkey.py`, `eu4_assistant_bot/main.py:151-245`.
- **Risk:** Advertised "F2 global hotkey" (README/CHANGELOG M5) likely does nothing in the running app.
- **Priority:** MED. Wire it into `run_with_ui`, ensure shutdown, and test start/stop + callback dispatch with a mock listener.

### FULL_BOT execution path — UNTESTED

- **What's not tested:** UI tests cover ASSIST no-op and the empty-plans case (`tests/test_ui.py:168-190`) but never SEMI_BOT (confirmation dialog) or FULL_BOT (no-dialog execute). The dangerous branch has zero coverage.
- **Files:** `tests/test_ui.py`, `eu4_assistant_bot/ui/main_window.py:159-185`.
- **Risk:** The exact code that would inject keystrokes without confirmation is unverified.
- **Priority:** MED.

### Watcher shutdown / atomic-rename / pause-timing — UNTESTED

- **What's not tested:** Timer-fire-after-stop, the EU4 temp-then-rename save pattern (`on_moved`), and GAME_PAUSED emission timing.
- **Files:** `tests/test_watcher.py`, `eu4_assistant_bot/watcher.py`.
- **Risk:** Missed saves / hung shutdown in real use.
- **Priority:** MED.

---

## Missing Critical Features

### FULL_BOT "real" action execution is a stub

- **Severity:** MED (expectation gap, not a regression)
- **Problem:** Despite "optional action automation" framing in `README`/`__init__.py:5` and a FULL_BOT mode, `ActionExecutor.execute()` only ever sends a pause key — there is no menu navigation or actual in-game action. The docstring defers this to "M9" (`executor.py:84-86`).
- **Blocks:** Any genuine automation; the SEMI/FULL distinction is currently cosmetic at the executor level.
- **Suggested action:** Either implement and gate it carefully (see safety entries) or clearly label these modes "experimental / advisory pause only" in user-facing docs to avoid over-promising.

---

*Concerns audit: 2026-06-23*
