## Conflict Detection Report

Inputs: 3 classified docs — 1 SPEC (EU4_ASSISTANT_BOT_DESIGN.md, authoritative v1.0),
2 DOC (CHANGELOG.md, README.md). Mode: new. Precedence: ADR > SPEC > PRD > DOC.
No ADRs present (no locked decisions possible). No UNKNOWN/low-confidence docs.
Cross-ref cycle check: no cycles (README references DESIGN/CHANGELOG/spec/LICENSE as
leaves; DESIGN and CHANGELOG have no outbound refs).

### BLOCKERS (0)

(none)

### WARNINGS (3)

[WARNING] Shipped version (0.5.0) contradicts design's "v1.0 (definitiva)" label
  Found: CHANGELOG.md header is "[0.5.0] — 2026-03-17" and notes "__init__.py now correctly
    reports 0.5.0"; EU4_ASSISTANT_BOT_DESIGN.md titles itself "Progettazione v1.0
    (definitiva)" and §11/§14 list M1–M10 complete with "v1.0 — Release stabile" as final.
  Impact: Downstream PROJECT.md/ROADMAP.md could mislabel maturity — the design calls the
    scope "v1.0 final / all milestones done" while the actual artifact version is 0.5.0.
    A reader can't tell if v1.0 has shipped or is the target of the 0.5.x line.
  → Confirm intent: is "v1.0" the design's target scope (and 0.5.0 the current build), or
    should the version be reconciled? Pick the canonical version string before roadmapping.

[WARNING] Hotkey/input library divergence: SPEC says pyautogui+win32api, CHANGELOG says pynput
  Found: EU4_ASSISTANT_BOT_DESIGN.md §6.5/§8.6 specify actions via `pyautogui` + `win32api`
    and name no library for the F2 hotkey listener; CHANGELOG.md M5 states
    "PauseController: hotkey listener via pynput".
  Impact: The tech stack for input handling spans two libraries (pynput for global hotkey
    listening, pyautogui/win32api for action execution). Not a direct contradiction (listen
    vs act are different concerns), but a downstream constraint/decision doc that records a
    single "input library" would be wrong.
  → Record both explicitly (pynput = hotkey listener; pyautogui+win32api = action executor)
    or confirm whether pynput should be folded out. Do not collapse to one library silently.

[WARNING] Operating-mode terminology skew: SPEC "Advisor" vs implemented "assist"
  Found: EU4_ASSISTANT_BOT_DESIGN.md §3 names the default mode "Advisor"; README.md CLI uses
    `--mode {assist,semi-bot,full-bot}` and CHANGELOG.md uses BotMode enum ASSIST/SEMI_BOT/
    FULL_BOT.
  Impact: Same three-mode concept, two vocabularies (user-facing "Advisor" vs CLI/code
    token "assist"). Requirements/UX docs and the CLI contract could drift if treated as
    distinct modes.
  → Confirm the canonical user-facing label vs the CLI/enum token (likely: display
    "Advisor", CLI token `assist`). Both are preserved in intel; pick the canonical name.

### INFO (5)

[INFO] No ADRs in ingest set — no locked decisions
  Note: All extracted decisions in decisions.md are SPEC-level (`spec-decision`), not
    locked. There are no ADR-vs-ADR or ADR-vs-existing-context blocker conditions possible
    in this ingest. SPEC (EU4_ASSISTANT_BOT_DESIGN.md) is the highest-precedence source
    present and won all precedence comparisons below.

[INFO] Auto-resolved: SPEC > DOC on milestone→feature mapping
  Note: The milestone-to-component mapping differs between the SPEC roadmap (DESIGN §11) and
    the CHANGELOG headers — e.g. ClausewitzTextParser is M3 in DESIGN but M1 in CHANGELOG;
    StateExtractor is M4 in DESIGN but M3 in CHANGELOG; M2 is "decision engine + simulated
    executor" in DESIGN but "State Reader & Models" in CHANGELOG. Per precedence (SPEC > DOC)
    the DESIGN roadmap mapping is treated as authoritative in synthesized intel; the
    CHANGELOG's "as-built" mapping is preserved verbatim in context.md for provenance. This
    is a historical/provenance divergence, not a forward-looking decision conflict.

[INFO] Additive (no conflict): modules/models present in DOCs but not enumerated in SPEC §8
  Note: README.md / CHANGELOG.md document `state_reader.py` (`SnapshotReader`),
    `save_adapter.py` (`SaveSnapshotAdapter`, legacy key=value), and the `WarState` model.
    The SPEC §8 module list and §9 snapshot do not enumerate these (SPEC §9 does list
    trade_nodes/provinces in JSON). These extend the SPEC without contradicting it — recorded
    in context.md and constraints.md (CON-gamesnapshot-schema) as additive deltas.

[INFO] "M1–M12" in orchestrator summary not supported by any source document
  Note: The ingest invocation described the CHANGELOG as "milestone history M1–M12", but all
    three source documents (DESIGN §11/§14, README "Stato progetto", CHANGELOG headers) only
    document milestones M1 through M10. No M11/M12 content exists to synthesize. Synthesized
    intel reflects the sources (M1–M10). Flagging so the discrepancy is visible; no source
    edit was made.

[INFO] No competing PRD acceptance variants
  Note: No PRDs were ingested, so there are no same-scope requirements with divergent
    acceptance criteria. All requirements in requirements.md derive from the SPEC's
    Definition of Done (§13) with single acceptance sets; CHANGELOG/README "shipped" notes
    are corroborating, not competing.
