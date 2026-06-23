# Constraints (Intel)

Technical constraints extracted from the authoritative SPEC (`EU4_ASSISTANT_BOT_DESIGN.md`).
type legend: api-contract | schema | nfr | protocol | platform.

---

## CON-no-external-api
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.1)
- type: protocol
- content: EU4 exposes no external API. The only reliable read channel is the autosave
  file. All state must be derived from `autosave.eu4`; no live IPC/socket/API into the game.

## CON-windows-platform
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§1, §2, §6.5);
  /mnt/c/Dev/eu4-assistant/README.md (Requisiti)
- type: platform
- content: Target runtime is Windows (Steam EU4, win32api, pyautogui). Python 3.11+.
  Tests run on any OS (offscreen Qt); the application proper runs on Windows. Dual-monitor
  context: EU4 fullscreen-borderless 2560x1440 on primary, companion on second monitor.

## CON-ironman-excluded
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§1, §6.2)
- type: nfr
- content: Ironman (binary Clausewitz) is explicitly out of scope for v1.0. Only text
  Clausewitz saves (ZIP-compressed) are supported.

## CON-defensive-dlc-parsing
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.3, §8.3)
- type: nfr
- content: Every parsed field must have a safe default; optional DLC sections (estates,
  parliaments, fervor, harmonization, …) are extracted if present and ignored if absent.
  A missing/unparsed DLC section must degrade gracefully, never crash.

## CON-zero-crash-stability
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§1, §13)
- type: nfr
- content: Primary non-functional objective — full stability from start to end of a campaign
  (1444 → end), zero crashes. This is the top priority; lower-priority features (e.g. auto
  pause) must not compromise it.

## CON-live-update-latency
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.1, §10)
- type: nfr
- content: Expected latency 1–3 seconds from autosave file written to UI updated. File
  watcher uses a 500ms debounce.

## CON-english-ui-template-matching
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.5, §8.6)
- type: protocol
- content: Action template matching must key on the English EU4 base UI, never on the IT
  translation mod's translated text, so the translation mod cannot break UI recognition.

## CON-mod-achievement-compatible
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§6.1, §8.9)
- type: protocol
- content: The companion autosave mod must not alter game rules and must remain
  achievement-compatible (only forces a monthly save).

## CON-peace-never-automated
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§4, §8.4b, §8.6)
- type: protocol
- content: Peace negotiations (and other critical actions: province cession, indemnity
  payments) must never be executed autonomously — always require explicit user confirmation.

## CON-gamesnapshot-schema
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§8.4, §9)
- type: schema
- content: `GameSnapshot` typed schema with sub-states EconomyState, MilitaryState
  (armies: list[ArmyState]), DiplomacyState, ColonialState, RiskState (coalition, rebels,
  ae_max), TechState (adm/dip/mil + monarch points), IdeasState. Canonical example payload
  in §9 (POR, 1460.06.01). Note: CHANGELOG/README add ProvinceState, TradeNodeState,
  WarState as `@dataclass(slots=True)` — see context.md / conflicts for the schema delta.

## CON-config-persistence-layout
- source: /mnt/c/Dev/eu4-assistant/EU4_ASSISTANT_BOT_DESIGN.md (§8.10)
- type: schema
- content: Persistence under `~/.eu4-assistant/`: `config.json`, `bot_params.json`,
  `changelog_seen.txt`. (Note: §9 snapshot example header in DESIGN references
  `~/.eu4-assistant/config.json + bot_params.json` in the architecture diagram §7.)

## CON-cli-surface
- source: /mnt/c/Dev/eu4-assistant/README.md (Opzioni CLI)
- type: api-contract
- content: CLI entry point `eu4-assistant` (and `python -m eu4_assistant_bot`). Flags:
  `--mode {assist,semi-bot,full-bot}` (default assist),
  `--risk-profile {safe,balanced,aggressive}`, `--install-path PATH`,
  `--snapshot-json PATH`, `--snapshot-save PATH`, `--watch SAVE_PATH`.
  (Mode token `assist` corresponds to SPEC's "Advisor" mode — see conflicts.)
