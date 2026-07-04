# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-27)

**Core value:** When EU4 writes an autosave, the app parses it and refreshes the UI with risk alerts + top-3 recommendations within a few seconds, with zero unhandled errors.
**Current focus:** Nessuna milestone attiva — slice colonista AUTO-01/02 implementata (navigation.Navigator + _execute_colonize, in PR); prossimo: milestone GSD v2 con safety hardening (kill-switch + opt-in FULL_BOT) come fase 1

## Current Position

Milestone "Make the live loop real": COMPLETA (4/4 fasi, PR #15, 2026-06-24)
Post-milestone: full-bot control surface + colonial province ranking mergiato (PR #17, 2026-06-27)
Post-milestone 2: slice colonista AUTO-01/02 (navigation.py, _execute_colonize, fix review: contiguità cv2, retry post-check, dims reali, push_log thread-safe) — branch feat/auto-colonize-slice
Status: Nessuna milestone attiva
Last activity: 2026-07-04 — slice AUTO-01/02 consolidata con fix da review interno; suite verde

Progress: [██████████] 100% (milestone completa; M1–M10 + live loop + control surface shipped)

## Performance Metrics

**Velocity:**
- Total plans completed: 0 (this milestone)
- Average duration: -
- Total execution time: -

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Ingest]: 10 SPEC-level design decisions treated as binding-but-not-locked (no ADRs).
- [Ingest]: M1–M10 are Validated (shipped, 132 unit tests); the next milestone repairs the loop that ties them together.
- [Phase 4]: Canonical version string settled at 0.5.0 (alpha); mode terminology mapped (Advisor/`assist`, Semi-bot/`semi-bot`, Full-bot/`full-bot`) — BUILD-02/03 done (PR #15).
- [Post-M]: PR #17 (2026-06-27) — full-bot control surface (Design A2: 4 states, params panel, persistent BotParams) + colonial province ranking + COLONIST_IDLE fix. 181 test.
- [Post-M2]: 2026-07-04 — slice colonista AUTO-01/02: Navigator (capture→match→click, lazy/soft-fail), contratto pre-check→execute→post-check con retry, targeting "nearest in view" su dims reali. Analisi profonda progetto: findings v2 registrati nel piano (fedeltà save reali, perf parser, DEBT confermati).

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

Nessun blocker aperto — live-loop/safety/version/wiring risolti da PR #15 (fasi 1-4); coverage live aggiunta (integration test `_process_save`, parser→extractor, safety gate).

Gap aperti tracciati come v2 (non bloccanti per funzionamento corrente): AUTO-01/02 (azioni reali in `execute()`), HARD-01/02/03 (hardening parser), DEBT-01/02/03 (tech debt). Vedi Deferred Items.

## Deferred Items

Items acknowledged and carried forward:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Automation | AUTO-01/02: slice colonize FATTA; restano asset live (template PNG su Windows+EU4) e altre categorie azione | v2 (in corso) | 2026-06-23 |
| Safety | Kill-switch hotkey + opt-in FULL_BOT persistito (precondizione uso unattended) | v2 fase 1 | 2026-07-04 |
| Parser | Recursion/size guards, streaming, atomic-rename handling; perf su gamestate reali 25-80MB | v2 (HARD-01/02/03) | 2026-06-23 |
| Fidelity | Fixture da autosave reale + audit chiavi (stability/prestige per-country, income/loan) | v2 | 2026-07-04 |
| Tech debt | Remove legacy parser (dead code confermato); consolidate coercion/adapters; lockfile | v2 (DEBT-01/02/03) | 2026-06-23 |

## Session Continuity

Last session: 2026-07-04
Stopped at: Slice AUTO-01/02 consolidata (fix review) su branch feat/auto-colonize-slice, PR in apertura; prossimo: gsd-new-milestone v2 (fase 1 = safety hardening).
Resume file: None
