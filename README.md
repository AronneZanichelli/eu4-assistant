# EU4 Assistant + Bot

Applicazione desktop companion per Europa Universalis IV: analisi in tempo reale,
raccomandazioni contestuali e automazione opzionale delle azioni di gioco.

Legge i salvataggi automatici di EU4 non appena vengono scritti, costruisce un
snapshot tipizzato dello stato di gioco e genera avvisi di rischio e consigli
strategici tramite una UI PyQt6 a tre colonne.

## Requisiti

- Python 3.11+
- Windows (per l'esecuzione con EU4; i test girano su qualsiasi OS)

## Installazione

```bash
git clone https://github.com/AronneZanichelli/eu4-assistant.git
cd eu4-assistant

# Sviluppo / test
pip install -e ".[dev]"

# Solo UI (advisor, dashboard, log)
pip install -e ".[ui]"

# UI + automazione (semi-bot / full-bot via pyautogui)
pip install -e ".[bot]"
```

## Utilizzo

### Modalità advisor — analisi one-shot da snapshot JSON

```bash
eu4-assistant --mode assist --snapshot-json snapshot.json
```

### Modalità UI live — file watcher + dashboard in tempo reale

```bash
eu4-assistant --watch "C:/Users/<utente>/Documents/Paradox Interactive/Europa Universalis IV/save games/autosave.eu4"
```

Oppure tramite modulo Python:

```bash
python -m eu4_assistant_bot --mode semi-bot --watch autosave.eu4
```

### Opzioni CLI

```
--mode {assist,semi-bot,full-bot}    Modalità di esecuzione (default: assist)
--risk-profile {safe,balanced,aggressive}
--install-path PATH                  Percorso installazione EU4
--snapshot-json PATH                 Snapshot JSON da analizzare
--snapshot-save PATH                 Save extract key=value da analizzare
--watch SAVE_PATH                    Avvia UI con file watcher sul save indicato
```

### Build eseguibile Windows

```bash
pip install -e ".[bot,pkg]"
pyinstaller eu4_assistant.spec --clean
# → dist/eu4-assistant.exe  (no console, standalone)
```

## Struttura progetto

```
eu4_assistant_bot/
├── __main__.py            # Abilita python -m eu4_assistant_bot
├── config.py              # AppConfig, BotMode, RiskProfile, soglie
├── parser.py              # ClausewitzTextParser (ricorsivo) + EU4RulesLoader
├── save_unzipper.py       # Decompressione save .eu4 (ZIP o plain text)
├── extractor.py           # Clausewitz tree → GameSnapshot tipizzato
├── watcher.py             # FileWatcher (watchdog) con debounce e pausa
├── decision_engine.py     # Risk alerts + top-3 raccomandazioni + action plans
├── executor.py            # ActionExecutor: simulate() + execute() mode-aware
├── models.py              # GameSnapshot e sotto-stati (dataclass slots)
├── pause_controller.py    # Pausa automatica EU4 su ribelli/guerra (F1)
├── state_reader.py        # Reader per snapshot JSON normalizzati
├── save_adapter.py        # Adapter per save extract key=value (legacy)
├── telemetry.py           # Structured logging + eventi JSONL
├── main.py                # CLI bootstrap + run_with_ui() pipeline
├── mod/                   # ModBuilder — genera mod autosave mensile EU4
└── ui/                    # Interfaccia PyQt6
    ├── main_window.py     # Finestra 3 colonne con tema scuro
    ├── dashboard_panel.py # Pannello sinistro — stato live
    ├── advisor_panel.py   # Pannello centrale — raccomandazioni + alert + Esegui
    ├── log_panel.py       # Pannello destro — feed eventi + filtri per livello
    └── hotkey.py          # F2 globale mostra/nascondi finestra
```

## Stato progetto

| Milestone | Contenuto | Stato |
|-----------|-----------|-------|
| M1–M4 | Foundation, parser, extractor, file watcher | ✅ |
| M5 | UI PyQt6 (Dashboard + Advisor + Log + PauseController) | ✅ |
| M6 | Military logic (army scoring, wartime manpower, fragmentation) | ✅ |
| M7 | Colonial + Economy advisor avanzato | ✅ |
| M8 | ActionExecutor reale (pyautogui) + pipeline UI live | ✅ |
| M9 | QA, SnapshotReader round-trip completo, test UI M8 | ✅ |
| M10 | Packaging PyInstaller + CHANGELOG + CLI entry point | ✅ |

## Documentazione

- **`CHANGELOG.md`** — storia completa delle modifiche M1–M10
- **`EU4_ASSISTANT_BOT_DESIGN.md`** — progettazione tecnica completa v1.0
- **`eu4_assistant.spec`** — configurazione build PyInstaller

## Licenza

MIT — vedi `LICENSE`.
