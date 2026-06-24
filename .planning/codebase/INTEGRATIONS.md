# External Integrations

**Analysis Date:** 2026-06-23

This is an offline desktop companion. There are **no network APIs, cloud services, databases, message queues, or auth providers**. A repo-wide scan for `requests`, `urllib`, `httpx`, `aiohttp`, `socket`, `websocket`, `openai`, `anthropic`, `boto3`, `sqlite3`, `psycopg`, and `redis` returned **zero matches** in `eu4_assistant_bot/`. Every integration below is a local OS / filesystem / game touchpoint.

## APIs & External Services

**None.** No HTTP clients, SDKs, or remote endpoints exist anywhere in the codebase. All "integration" is with the local Europa Universalis IV installation, the local filesystem, and the OS input/window layer.

## Game Integration: EU4 Save Files (read)

**EU4 autosave / manual save (`.eu4`):**
- Consumed by `eu4_assistant_bot/save_unzipper.py` (`SaveUnzipper.extract_gamestate`).
- Format detection by magic bytes: files starting with `PK` are treated as ZIP archives; everything else is read as plain UTF-8 text.
- ZIP saves contain `meta`, `gamestate`, `ai` entries; the `gamestate` entry is extracted (fallback: first non-`meta` entry). Decode uses `errors="replace"`.
- **Ironman binary saves are explicitly out of scope** (docstring in `save_unzipper.py`).
- Decoded gamestate text is parsed by the recursive `ClausewitzTextParser` (`eu4_assistant_bot/parser.py`) into a nested dict, then projected into a typed `GameSnapshot` by `eu4_assistant_bot/extractor.py` (`StateExtractor.extract`).
- Typical path (from README): `C:/Users/<user>/Documents/Paradox Interactive/Europa Universalis IV/save games/autosave.eu4`.

**Alternative snapshot inputs (no `.eu4` needed):**
- `--snapshot-json PATH` → normalized JSON snapshot read by `eu4_assistant_bot/state_reader.py` (`SnapshotReader`, full JSON round-trip into `GameSnapshot`).
- `--snapshot-save PATH` → legacy `key=value` extract read by `eu4_assistant_bot/save_adapter.py` (`SaveSnapshotAdapter`).

## Game Integration: EU4 Rules Files (read)

**Install-directory definitions:**
- `eu4_assistant_bot/parser.py` → `EU4RulesLoader.load_rules_index()` reads `.txt` rule files from the EU4 install path:
  - `common/units/*.txt`
  - `common/ideas/*.txt`
  - `common/event_modifiers/*.txt`
- Mod overrides supported via `mod_paths` (later entries override earlier; per-file replacement by `file.stem`).
- Missing folders are silently skipped (`_load_folder` returns if the folder does not exist), so a wrong/absent install path degrades to an empty rules index rather than crashing.
- Default install path: `~/Games/Europa Universalis IV` (`config.py`); overridable with `--install-path`.

## Game Integration: EU4 Mod Generation (write)

**Generated mod — "EU4 Assistant - Monthly Autosave":**
- Built/installed by `eu4_assistant_bot/mod/mod_builder.py` (`ModBuilder.install`).
- Writes three Clausewitz-format files into the EU4 mod folder (idempotent — re-install of same version returns `SKIPPED`):
  - `<mod_folder>/eu4_assistant_autosave.mod` — descriptor (`name`, `supported_version`, `path`). Default `supported_version = "1.37.*"`.
  - `<mod_folder>/eu4_assistant_autosave/events/monthly_save.txt` — hidden `country_event` (`id = eu4_assistant.1`) whose `immediate` block runs `save_game = yes`.
  - `<mod_folder>/eu4_assistant_autosave/common/on_actions/eu4_assistant.txt` — hooks `on_monthly_pulse` to fire `eu4_assistant.1` every in-game month.
- Purpose: force EU4 to emit a fresh save every in-game month so the watcher always has current state without manual saving.
- Target folder convention: `Documents/Paradox Interactive/Europa Universalis IV/mod`.

## File Watching (OS filesystem events)

**Autosave watcher:**
- `eu4_assistant_bot/watcher.py` (`FileWatcher`) uses **watchdog** (`Observer` + `FileSystemEventHandler`) to monitor the save file's parent directory (non-recursive).
- Filters events to the exact target path (resolved), debounces rapid writes (default 0.5s via `threading.Timer`), and emits `SaveEvent` objects on a thread-safe `queue.Queue`.
- Two event types (`SaveEventType`): `SAVE_CHANGED` (file written) and `GAME_PAUSED` (no save within `pause_timeout`, default 180s — inferred "EU4 paused or closed").
- Background daemon thread (`eu4-pause-monitor`) polls every 10s to emit `GAME_PAUSED`.
- Driven by `run_with_ui()` in `main.py`, which consumes the queue and pushes parsed snapshots into the PyQt6 window.

## OS-Level Automation (keystrokes & hotkeys)

**Outbound keystrokes to EU4 (game control):**
- `eu4_assistant_bot/executor.py` → `ActionExecutor._pause_game()` sends **Space** via **pyautogui** (`pyautogui.press("space")`) to toggle EU4 pause during `SEMI_BOT`/`FULL_BOT` execution. If pyautogui is not installed (`bot` extra absent), it logs a warning and returns advisory-only (no crash).
- `eu4_assistant_bot/pause_controller.py` → `PauseController` sends **F1** to pause EU4 on critical conditions (rebels imminent `risk.rebels >= 0.60`, or a newly detected war). Platform-dependent key delivery via `_default_send_key`:
  - **Linux:** shells out to the external `xdotool` binary (`subprocess.run(["xdotool","key",key])`, 3s timeout). No-ops with a warning if `xdotool` is missing.
  - **Windows / macOS:** uses **pynput** `keyboard.Controller` press/release.

**Global hotkey (window control):**
- `eu4_assistant_bot/ui/hotkey.py` → `HotkeyManager` uses **pynput** `keyboard.Listener` to listen globally for **F2** and toggle show/hide of the main window. Listener runs as a daemon thread.

Mode gating (`config.py` `BotMode`): `ASSIST` = advisory only, never sends game keystrokes; `SEMI_BOT` = pause + UI confirmation before acting; `FULL_BOT` = direct execution (currently same pause behavior as SEMI_BOT per CHANGELOG M8).

## Data Storage (local files only)

**App data directory:** `~/.eu4-assistant/` (created by `AppConfig.bootstrap_dirs`):
- `logs/eu4-assistant.log` — rotating file log (5 MB × 3 backups, `telemetry.setup_logging`).
- `snapshots/last_snapshot.json` — last parsed `GameSnapshot`, written via `GameSnapshot.save` (`models.py`).
- `events.jsonl` — structured session events (see Telemetry below).

**Databases / caches / object storage:** None. No SQLite, no ORM, no remote DB, no Redis, no S3/blob storage. Persistence is plain JSON / JSONL / log files on the local disk.

**Secrets:** None. No `.env`, no credential files, no API keys anywhere (none required — fully offline).

## Telemetry & Observability (local)

**Structured event log (JSONL):**
- `eu4_assistant_bot/telemetry.py` → `emit_event()` appends one JSON object per line to `~/.eu4-assistant/events.jsonl`.
- `run()` emits a `startup` event capturing mode, risk profile, rules-index counts, snapshot source/path/error, risk alerts, action plans, execution results/summary, and recommendations (`main.py`).
- Enums serialized via a custom `_json_default`. Write failures are swallowed (logged, never raised).

**Logging:**
- `setup_logging()` configures a rotating file handler + console `StreamHandler`, format `%(asctime)s [%(levelname)s] %(name)s: %(message)s`, level from `AppConfig.log_level` (default `INFO`).

**Error tracking:** None (no Sentry / external APM). Errors surface in the rotating log, the JSONL event stream, and the in-app Log panel (`eu4_assistant_bot/ui/log_panel.py`).

## CI/CD & Deployment

**Hosting / distribution:**
- No server deployment. Distributed as a standalone Windows executable `dist/eu4-assistant.exe` built by PyInstaller.

**CI pipeline (GitHub Actions):**
- `.github/workflows/ci.yml` — tests on push (all branches) and PRs to `main`; Python 3.11/3.12 on Ubuntu, headless Qt.
- `.github/workflows/build.yml` — on `v*` tags, builds the Windows `.exe` on `windows-latest` and uploads it as a build artifact (`actions/upload-artifact@v4`). No publishing to PyPI or any package registry.

## Environment Configuration

**Required env vars:** None. The app reads no environment variables at runtime; all paths default from `Path.home()` and are overridable via CLI flags (`--install-path`, `--snapshot-json`, `--snapshot-save`, `--watch`). `QT_QPA_PLATFORM=offscreen` is set only inside CI for headless tests.

**Secrets location:** Not applicable — no secrets exist.

## Webhooks & Callbacks

**Incoming:** None (no HTTP server, no listening sockets).

**Outgoing:** None (no outbound network calls). The only "callbacks" are in-process: watchdog → queue → `run_with_ui` loop, and `PauseController.on_pause` / `HotkeyManager` callbacks.

---

*Integration audit: 2026-06-23*
