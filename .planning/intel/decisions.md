# Decisions (Intel)

Synthesized from classified docs. No ADRs were present in the ingest set, so there are
no formally locked architectural decisions. The entries below are **technical decisions
extracted from the authoritative SPEC** (`EU4_ASSISTANT_BOT_DESIGN.md`, v1.0) — they carry
SPEC precedence but are not locked. Treat them as the design's binding choices unless a
future ADR supersedes them.

status legend: `spec-decision` = asserted by the authoritative SPEC; not locked.

---

## DEC-data-source-autosave-watch
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.1)
- status: spec-decision
- decision: EU4 exposes no external API; the only reliable read channel is the
  `autosave.eu4` file. A `watchdog`-based file watcher monitors it; a lightweight
  companion mod forces a monthly in-game save (achievement-compatible).
- scope: data acquisition pipeline

## DEC-save-format-clausewitz-text
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.2)
- status: spec-decision
- decision: Save files are Clausewitz text compressed in ZIP. A custom recursive Python
  parser handles full Clausewitz text; `SaveUnzipper` handles ZIP decompression
  pre-parsing. Ironman (binary Clausewitz) is out of scope for v1.0.
- scope: parsing / save format

## DEC-dlc-defensive-parsing
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.3)
- status: spec-decision
- decision: Defensive parsing — every field has a safe default if absent; optional DLC
  sections (estates, parliaments, fervor, harmonization, …) extracted if present, ignored
  if absent; graceful degradation rather than crash; tested against sample saves across
  DLC combinations.
- scope: DLC compatibility / robustness

## DEC-ui-pyqt6-second-monitor
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.4)
- status: spec-decision
- decision: A standard (non-overlay) PyQt6 window on the second monitor. PyQt6 chosen for
  native Windows widgets, full dark-theme control, and easy PyInstaller packaging. Window
  remembers position and size between sessions.
- scope: UI framework / presentation

## DEC-action-execution-pyautogui-win32
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.5, §8.6)
- status: spec-decision
- decision: Semi/Full-bot actions executed via `pyautogui` + `win32api`. Template matching
  is keyed on the English EU4 base UI (not the IT translation mod) so the translation mod
  cannot interfere with UI recognition. Each action: pre-check (template match) → execute →
  post-check → fallback+log on mismatch.
- scope: action executor / input automation

## DEC-single-active-mode
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§3)
- status: spec-decision
- decision: Exactly one operating mode is active at a time — Advisor (default), Semi-bot
  (per single action, returns to Advisor after), or Full-bot (global switch with
  configurable guardrails, instantly disableable, params persisted across sessions).
- scope: operating-mode model

## DEC-peace-gate-always-manual
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§4, §8.4b, §8.5, §8.6)
- status: spec-decision
- decision: Peace negotiations are never automated. Critical actions (peace deals,
  province cession, indemnity payments) always stop the bot and require explicit user
  confirmation, with an "undo last action" available only for these critical actions.
- scope: bot safety policy

## DEC-config-persistence-home-dir
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.6, §8.10)
- status: spec-decision
- decision: On first launch the app auto-detects the EU4 install folder and the Paradox
  Documents folder (manual selection dialog as fallback). Persistence under
  `~/.eu4-assistant/`: `config.json` (paths, UI prefs, active mode, hotkey),
  `bot_params.json` (full-bot params), `changelog_seen.txt` (last changelog version shown).
- scope: configuration / persistence

## DEC-auto-pause-low-priority
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§5.1, §8.7)
- status: spec-decision
- decision: The app sends `F1` (EU4 pause) automatically on imminent rebellion (max unrest)
  or war declared against the player. Explicitly flagged low-priority and must not impact
  stability.
- scope: automated pause behavior

## DEC-scope-v1-no-ironman
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§1 Scope, §6.2)
- status: spec-decision
- decision: v1.0 scope = normal campaigns with all DLC active and graphical/QoL mods.
  Ironman is excluded. Primary objective: full stability start-to-finish, zero crashes.
- scope: project scope boundary
