# Context (Intel)

Running notes from DOC-type sources (`CHANGELOG.md`, `README.md`), keyed by topic, with
source attribution. These are informational/historical and rank below the SPEC.

---

## Topic: project overview
- source: /mnt/c/Dev/eu4-assistant/README.md (intro)
- A desktop companion for Europa Universalis IV: real-time analysis, contextual
  recommendations, and optional game-action automation. Reads EU4 autosaves as they are
  written, builds a typed game-state snapshot, and surfaces risk alerts + strategic advice
  via a 3-column PyQt6 UI. UI language Italian.

## Topic: install / extras
- source: /mnt/c/Dev/eu4-assistant/README.md (Installazione)
- Repo: https://github.com/AronneZanichelli/eu4-assistant.git
- Pip extras: `[dev]` (development/test), `[ui]` (advisor/dashboard/log only), `[bot]`
  (UI + automation via pyautogui), `[pkg]` (PyInstaller, per CHANGELOG `pyinstaller>=5.0,<7.0`).
- License: MIT.

## Topic: module map (as built)
- source: /mnt/c/Dev/eu4-assistant/README.md (Struttura progetto)
- Package `eu4_assistant_bot/` with: `__main__.py`, `config.py`, `parser.py`,
  `save_unzipper.py`, `extractor.py`, `watcher.py`, `decision_engine.py`, `executor.py`,
  `models.py`, `pause_controller.py`, `state_reader.py`, `save_adapter.py`, `telemetry.py`,
  `main.py`, `mod/`, and `ui/` (`main_window.py`, `dashboard_panel.py`, `advisor_panel.py`,
  `log_panel.py`, `hotkey.py`).
- NOTE — modules present in the built package but NOT explicitly enumerated in the SPEC's
  module list (§8): `state_reader.py` (`SnapshotReader`) and `save_adapter.py`
  (`SaveSnapshotAdapter`, legacy key=value reader). Additive vs SPEC — see INGEST-CONFLICTS.

## Topic: model set (as built)
- source: /mnt/c/Dev/eu4-assistant/CHANGELOG.md (M2, M3, M9)
- `GameSnapshot` and all sub-models implemented as `@dataclass(slots=True)` with safe
  defaults: EconomyState, MilitaryState, DiplomacyState, ColonialState, RiskState,
  TechState, IdeasState, TradeNodeState, ProvinceState, ArmyState, WarState.
- `SnapshotReader`: JSON snapshot loader with `_safe_dict()` null tolerance; M9 added full
  round-trip reconstruction of `trade_nodes` (list[TradeNodeState]) and `provinces`
  (list[ProvinceState]).
- `SaveSnapshotAdapter`: legacy key=value format reader.
- NOTE — `WarState` and `ProvinceState`/`TradeNodeState` as first-class models extend the
  SPEC §9 snapshot, which lists trade_nodes/provinces in the JSON but does not enumerate
  WarState. Additive; SPEC is silent, not contradicted.

## Topic: decision-engine risk codes (as built)
- source: /mnt/c/Dev/eu4-assistant/CHANGELOG.md (M1, M6, M7)
- Scaffold: `evaluate_risks()`, `recommend()`, `build_action_plans()`.
- RiskCodes: `ARMY_BELOW_FORCE_LIMIT`, `ARMY_FRAGMENTED`, `WARTIME_MANPOWER_LOW`
  (M6); `COLONIST_IDLE`, `MERCHANT_UNDEPLOYED`, `TECH_AFFORDABLE` (M7).
- `DecisionThresholds`: `army_strength_threshold`, `wartime_manpower_min`.
- `RISK_PROFILE_PRESETS` for SAFE/BALANCED/AGGRESSIVE.

## Topic: executor behavior (as built)
- source: /mnt/c/Dev/eu4-assistant/CHANGELOG.md (M1, M8)
- M1: `ActionExecutor.simulate()` mode-aware (ASSIST skips, SEMI_BOT/FULL_BOT execute).
- M8: `ActionExecutor.execute()` mode-aware — ASSIST=advisory, SEMI_BOT=confirm dialog +
  pyautogui pause, FULL_BOT=direct execute. `run_with_ui()` in `main.py` runs the live
  FileWatcher → DecisionEngine → MainWindow pipeline in a daemon thread.
- BotMode enum tokens: ASSIST / SEMI_BOT / FULL_BOT (maps to SPEC modes Advisor / Semi-bot
  / Full-bot — naming skew noted in conflicts).

## Topic: input/hotkey library (as built)
- source: /mnt/c/Dev/eu4-assistant/CHANGELOG.md (M5)
- `PauseController`: hotkey listener via `pynput`.
- NOTE — SPEC names `pyautogui` + `win32api` for action execution (§6.5) but does not name
  a library for the F2 hotkey listener; CHANGELOG uses `pynput` for that. Different concern
  (listen vs act). Divergence flagged as a WARNING in INGEST-CONFLICTS for tech-stack clarity.

## Topic: CI / build (as built)
- source: /mnt/c/Dev/eu4-assistant/CHANGELOG.md (M1, M5, M10)
- GitHub Actions matrix (Python 3.11, 3.12), pytest offscreen (`QT_QPA_PLATFORM=offscreen`,
  `libegl1`).
- M10: PyInstaller `.spec` for `eu4-assistant.exe`; `[project.scripts]` entry point;
  GitHub Actions build workflow on `v*` tags; `__init__.py` version corrected to `0.5.0`.

## Topic: release/version status
- source: /mnt/c/Dev/eu4-assistant/CHANGELOG.md (header [0.5.0]); DESIGN title (v1.0)
- Latest CHANGELOG release: `[0.5.0] — 2026-03-17`; `__init__.py` reports `0.5.0`.
- DESIGN document titles itself "Progettazione v1.0 (definitiva)" and §11/§14 mark M1–M10
  all complete with "v1.0 — Release stabile" as the final line.
- DISCREPANCY — shipped version (0.5.0) vs design target label (v1.0). Flagged as WARNING.

## Topic: milestone status (as reported)
- source: DESIGN §11/§14, README "Stato progetto", CHANGELOG headers
- All three docs report milestones M1 through M10 complete. None of the source documents
  mentions M11 or M12 (the orchestrator's "M1–M12" summary is not supported by any source —
  see INGEST-CONFLICTS INFO note).
- Milestone→feature mapping differs between DESIGN (§11) and CHANGELOG headers (e.g.
  ClausewitzParser: DESIGN M3 vs CHANGELOG M1; StateExtractor: DESIGN M4 vs CHANGELOG M3;
  M2: DESIGN "decision engine + simulated executor" vs CHANGELOG "State Reader & Models").
  Provenance divergence flagged in INGEST-CONFLICTS (SPEC mapping takes precedence).
