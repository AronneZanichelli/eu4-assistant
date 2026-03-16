# EU4 Assistant + Bot

Applicazione desktop companion per Europa Universalis IV: analisi in tempo reale, raccomandazioni contestuali e automazione opzionale delle azioni di gioco.

## Requisiti

- Python 3.11+
- Windows (per l'esecuzione con EU4; i test girano su qualsiasi OS)

## Setup sviluppo

```bash
git clone https://github.com/AronneZanichelli/eu4-assistant.git
cd eu4-assistant
pip install -e ".[dev]"
python -m pytest -q
```

## Struttura progetto

```
eu4_assistant_bot/
├── config.py            # AppConfig, BotMode, RiskProfile, soglie
├── parser.py            # ClausewitzTextParser (ricorsivo) + EU4RulesLoader
├── save_unzipper.py     # Decompressione save .eu4 (ZIP o plain text)
├── extractor.py         # Clausewitz tree → GameSnapshot tipizzato
├── watcher.py           # FileWatcher (watchdog) con debounce e pausa
├── decision_engine.py   # Risk alerts + top-3 raccomandazioni
├── executor.py          # ActionExecutor (simulato, M8 per reale)
├── models.py            # GameSnapshot e sotto-stati (dataclass)
├── mod/                 # ModBuilder — genera mod autosave mensile EU4
├── save_adapter.py      # Adapter per save extract key=value
├── state_reader.py      # Reader per snapshot JSON normalizzati
├── telemetry.py         # Structured logging + eventi
└── main.py              # CLI bootstrap
```

## Stato progetto

| Milestone | Stato |
|---|---|
| M1 — Foundation | ✅ |
| M2 — Decision engine + simulated executor | ✅ |
| M3 — ClausewitzTextParser + SaveUnzipper + mod | ✅ |
| M4 — FileWatcher + StateExtractor + DLC compat | ✅ |
| M5 — UI PyQt6 + PauseController + hotkey | ⏳ Prossimo |
| M6 — Military logic | 🔜 |
| M7 — Colonial + Economy logic | 🔜 |
| M8 — ActionExecutor reale + full-bot UI | 🔜 |
| M9 — QA / stabilità / crash hardening | 🔜 |
| M10 — Packaging + changelog + docs | 🔜 |

## Documentazione

- **`EU4_ASSISTANT_BOT_DESIGN.md`** — Progettazione completa v1.0
- **`M3_PLAN.md`** — Piano implementazione M3 (completato)
- **`CLAUDE_CODE_HANDOFF.md`** — Briefing tecnico con bug noti e migliorie pianificate

## Licenza

MIT — vedi `LICENSE`.
