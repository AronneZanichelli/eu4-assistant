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
- ✓ 181 unit tests passing across 14+ modules (PR #15 integration tests + PR #17 control surface tests)

Note: "Validated" here means shipped and unit-tested. The live watch pipeline is end-to-end functional as of PR #15.

### Completato (milestone v0.6 "Make the live loop real")

<!-- Shipped in PR #15, 2026-06-24. -->

- [x] Live watch pipeline produces snapshots and refreshes the UI on every save (fix `parse` bug; tighten error handling; add integration test)
- [x] Auto-pause and the F2 global show/hide work end-to-end (wire `PauseController` + `HotkeyManager`; fix F1→Space pause key)
- [x] Real bot actions (semi-bot/full-bot) are gated by an explicit confirmation contract enforced in the executor, with a window-focus guard and a failsafe
- [x] Python-version and CI drift reconciled so the supported/tested interpreter matches the runtime, and the canonical version/terminology are settled

### Post-Milestone (PR #17, 2026-06-27)

- [x] Full-bot control surface: 4 stati, params panel persistente, switch-off immediato (Design A2)
- [x] Colonial province ranking + fix COLONIST_IDLE

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

**Known issues (risolti da PR #15, 2026-06-24):**
Tutti i bug segnalati dal codebase map (2026-06-23) sono stati risolti nella milestone "Make the live loop real": `parse`→`parse_text`, except-handling granulare, pause key Space unificata, PauseController+HotkeyManager wired, safety gate enforced in `execute()`, CI/version drift corretto, pynput lazy-import, integration tests aggiunti. Vedi PR #15 per i dettagli.

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
| Read state from `autosave.eu4` via a watchdog file watcher + companion monthly-save mod | EU4 has no external API; the file is the only reliable channel | ✓ Good (PR #15 Phase 1) |
| Custom recursive Clausewitz text parser + ZIP unzipper; Ironman excluded | Full text-save fidelity; binary is a separate large effort | ✓ Good |
| Defensive DLC parsing with safe defaults | Survive any DLC combination without crashing | ✓ Good |
| Standard (non-overlay) PyQt6 window on the second monitor | Native Windows widgets, dark theme, easy PyInstaller packaging | ✓ Good |
| Actions via `pyautogui` + `win32api`; template-match on English base UI | Translation mod cannot break UI recognition | ✓ Good (SAFE-03 focus guard + failsafe — PR #15); template-match reale deferred AUTO-02 |
| Exactly one active operating mode (Advisor / Semi-bot / Full-bot) | Clear, predictable bot behaviour | ✓ Good |
| Peace and other critical actions always manual, with undo | Never let the bot make irreversible diplomatic decisions | ✓ Good (enforced in execute(), SAFE-01/02 — PR #15) |
| Config persisted under `~/.eu4-assistant/` (`config.json`, `bot_params.json`, `changelog_seen.txt`) | Predictable, user-owned persistence | ✓ Good |
| Auto-pause (Space) on imminent rebellion / war, flagged low-priority | Give the player a chance to react; must not hurt stability | ✓ Good (Space, wired, PAUSE-01/02 — PR #15) |
| v1.0 scope = normal campaigns, all DLC, QoL mods; Ironman excluded | Keep scope tractable; stability first | ✓ Good |
| Canonical version string / terminology settled (0.5.0 alpha; "Advisor"/`assist`, "Semi-bot"/`semi-bot`, "Full-bot"/`full-bot`) | Avoid misrepresenting maturity and drift between UI and CLI | ✓ Settled (BUILD-02/03 — PR #15) |

---
*Last updated: 2026-06-27 — milestone "Make the live loop real" completa (PR #15); post-milestone PR #17 mergiata; doc riconciliati*
