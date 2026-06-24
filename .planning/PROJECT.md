# EU4 Assistant + Bot

## What This Is

A Windows desktop companion for Europa Universalis IV. It watches the game's
`autosave.eu4` as it is written, parses the Clausewitz text save into a typed
`GameSnapshot`, and surfaces risk alerts plus the top-3 strategic recommendations
in a 3-column PyQt6 window (Dashboard / Advisor / Log). It can optionally execute
single recommended actions (semi-bot) or run autonomously (full-bot) via keystroke
automation, with peace and other critical actions always left to the player.

For one player running EU4 fullscreen on a primary monitor with the companion on a
second monitor. Built and maintained by a solo developer with Claude as the implementer.

## Core Value

When EU4 writes an autosave, the app parses it and refreshes the UI with risk
alerts and top-3 recommendations within a few seconds, with zero unhandled errors.
**If everything else fails, the live watch → parse → snapshot → UI loop must work.**

## Requirements

### Validated

<!-- Shipped (M1–M10) and relied upon. Code-confirmed by the codebase map. -->

- ✓ Recursive Clausewitz text parser + ZIP unzipper (`ClausewitzTextParser`, `SaveUnzipper`) — M1/M4
- ✓ State extractor producing a typed `GameSnapshot` with defensive defaults (`StateExtractor`) — M2/M3
- ✓ `watchdog`-based file watcher with debounce + `GAME_PAUSED` detection (`FileWatcher`) — M4
- ✓ 3-column PyQt6 UI: Dashboard / Advisor / Log, dark theme, geometry persisted — M5
- ✓ Military + colonial + economy advisors with risk codes and top-3 recommendations — M6/M7
- ✓ Real `ActionExecutor` (pyautogui) with mode-aware `execute()` and CLI `simulate()` — M8
- ✓ Companion autosave mod (`ModBuilder`, monthly save, achievement-compatible) — M1
- ✓ Path auto-detect + `~/.eu4-assistant/` config persistence — M4
- ✓ Log panel with level filters + CSV export + JSONL telemetry — M1/M5
- ✓ Changelog-on-update system (`changelog_seen.txt`) — M10
- ✓ PyInstaller Windows `.exe` build + CLI entry point + GitHub Actions — M10
- ✓ 132 unit tests passing across 14 modules

Note: "Validated" here means shipped and unit-tested. The live watch pipeline that
ties these together is **not** end-to-end functional — see Context and the roadmap.

### Active

<!-- Current scope: the v0.6 "Make the live loop real" milestone. -->

- [ ] Live watch pipeline produces snapshots and refreshes the UI on every save (fix `parse` bug; tighten error handling; add integration test)
- [ ] Auto-pause and the F2 global show/hide work end-to-end (wire `PauseController` + `HotkeyManager`; fix F1→Space pause key)
- [ ] Real bot actions (semi-bot/full-bot) are gated by an explicit confirmation contract enforced in the executor, with a window-focus guard and a failsafe
- [ ] Python-version and CI drift reconciled so the supported/tested interpreter matches the runtime, and the canonical version/terminology are settled

### Out of Scope

<!-- Explicit boundaries, with reasoning. -->

- Ironman / binary Clausewitz saves — out of scope for v1.0 by design (only ZIP text saves supported); binary parsing is a large, separate effort
- Live IPC/socket/API into EU4 — the game exposes no external API; the autosave file is the only reliable read channel
- Automating peace deals, province cession, indemnity payments — must always require explicit user confirmation (safety policy)
- Cross-platform GUI runtime as a supported target — EU4 runs elsewhere but the app targets Windows; Linux/macOS send-key branches stay experimental
- Localizing template matching to the Italian translation mod — matching keys on the English base UI so the translation mod cannot break recognition
- Full menu-navigation automation for arbitrary in-game actions — `execute()` currently only sends a pause key; broad automation is deferred beyond this milestone

## Context

**Technical environment:**
- Python 3.11+, package `eu4_assistant_bot`, current version `0.5.0` (Alpha)
- PyQt6 GUI (optional extras: `[ui]`, `[bot]`, `[pkg]`); only `watchdog` is a base dependency
- Windows is the runtime target (Steam EU4, win32api, pyautogui); tests run headless cross-platform (`QT_QPA_PLATFORM=offscreen`)
- CI matrix: Python 3.11 / 3.12 on ubuntu-latest; release build on windows-latest → `dist/eu4-assistant.exe`

**Known issues to address (from the codebase map, 2026-06-23):**
- **HIGH — live UI pipeline calls a non-existent parser method.** `main.py:201` calls `ClausewitzTextParser().parse(...)`; the class only defines `parse_text()` / `parse_file()` (`parser.py:182`, `:191`). Every live save raises `AttributeError`.
- **HIGH — over-broad `except (SaveFormatError, Exception)`** at `main.py:203` swallows that bug (and any `TypeError`/`KeyError`/`RecursionError`) into one generic log line, so the flagship feature is silently broken with a green test suite.
- **MED — auto-pause presses the wrong key.** `PauseController._send_key("F1")` (`pause_controller.py:73`) opens a ledger panel; the actual EU4 pause is Space, which `ActionExecutor._pause_game()` already uses (`executor.py:141`).
- **Incomplete wiring.** `PauseController` and `ui/hotkey.py` `HotkeyManager` are implemented and unit-tested but never instantiated in `run_with_ui()` / `MainWindow`, so auto-pause and the F2 toggle do nothing end-to-end.
- **HIGH (safety) — FULL_BOT executes with no confirmation;** `ActionPlan.requires_confirmation` is honoured in `simulate()` but ignored in `execute()` (`executor.py:77-123`); no window-focus check and no `pyautogui.FAILSAFE`.
- **MED — version/CI drift.** `requires-python>=3.11`, CI tests 3.11/3.12, but the in-repo interpreter is 3.14; `pynput` is imported at module top-level in `ui/hotkey.py`, so a failed `pynput` build breaks the whole UI import.
- **Coverage gap.** No test references `run_with_ui` / `_process_save` / `_watcher_loop`; parser→extractor integration is also untested (extractor is only fed a hand-built dict).

**Doc inconsistencies (non-blocking, to reconcile):**
- Version `0.5.0` (CHANGELOG/`__init__.py`) vs design label "v1.0 (definitiva)"
- CHANGELOG documents M1–M10; git history has M11/M12 commits (no source doc describes them)
- Mode label "Advisor" (design/UI) vs CLI/enum token `assist`
- Input libraries span `pynput` (hotkey listener) and `pyautogui`+`win32api` (action execution) — both are legitimate, different concerns

## Constraints

- **Data source**: All game state must come from `autosave.eu4` — EU4 exposes no external API; no live IPC/socket
- **Save format**: Clausewitz text in ZIP only; Ironman (binary) excluded for v1.0
- **DLC robustness**: Defensive parsing — every field has a safe default; optional DLC sections degrade gracefully, never crash
- **Stability**: Zero crashes start-to-finish of a campaign is the top non-functional priority; lower-priority features (auto-pause) must not compromise it
- **Latency**: 1–3 seconds from autosave written to UI updated; watcher uses a 500ms debounce
- **Safety — peace gate**: Peace, province cession, and indemnity payments are never automated; always require explicit user confirmation
- **Safety — input**: Template matching keys on the English base UI, not the Italian translation mod
- **Platform**: Windows runtime (win32api, pyautogui); Python 3.11+; tests run on any OS headless
- **UI language**: Italian (user-facing strings)
- **Tech stack**: PyQt6 (UI), `watchdog` (file events), `pynput` (hotkey listener), `pyautogui`+`win32api` (action execution); `pyinstaller` (build)
- **CLI contract**: `eu4-assistant` with `--mode {assist,semi-bot,full-bot}`, `--risk-profile {safe,balanced,aggressive}`, `--install-path`, `--snapshot-json`, `--snapshot-save`, `--watch`

## Key Decisions

<!-- 10 SPEC-level design decisions (not ADR-locked) + reconciliation decisions for this milestone. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Read state from `autosave.eu4` via a watchdog file watcher + companion monthly-save mod | EU4 has no external API; the file is the only reliable channel | — Pending (live loop broken, fix in Phase 1) |
| Custom recursive Clausewitz text parser + ZIP unzipper; Ironman excluded | Full text-save fidelity; binary is a separate large effort | ✓ Good (parser works; live wiring broken) |
| Defensive DLC parsing with safe defaults | Survive any DLC combination without crashing | ✓ Good |
| Standard (non-overlay) PyQt6 window on the second monitor | Native Windows widgets, dark theme, easy PyInstaller packaging | ✓ Good |
| Actions via `pyautogui` + `win32api`; template-match on English base UI | Translation mod cannot break UI recognition | — Pending (no focus guard / failsafe yet) |
| Exactly one active operating mode (Advisor / Semi-bot / Full-bot) | Clear, predictable bot behaviour | ✓ Good |
| Peace and other critical actions always manual, with undo | Never let the bot make irreversible diplomatic decisions | ⚠️ Revisit (confirmation not enforced in `execute()`) |
| Config persisted under `~/.eu4-assistant/` (`config.json`, `bot_params.json`, `changelog_seen.txt`) | Predictable, user-owned persistence | ✓ Good |
| Auto-pause (Space) on imminent rebellion / war, flagged low-priority | Give the player a chance to react; must not hurt stability | ⚠️ Revisit (currently sends F1, not wired) |
| v1.0 scope = normal campaigns, all DLC, QoL mods; Ironman excluded | Keep scope tractable; stability first | ✓ Good |
| Canonical version string / terminology to be settled (0.5.0 vs "v1.0"; "Advisor" vs `assist`) | Avoid misrepresenting maturity and drift between UI and CLI | — Pending (Phase 4) |

---
*Last updated: 2026-06-23 after new-project ingest (M1–M10 shipped; next milestone = make the live loop real)*
