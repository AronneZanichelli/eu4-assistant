# EU4 Assistant Bot — Handoff per Claude Code

> Questo file è il briefing completo per continuare lo sviluppo del progetto.
> Generato da una sessione di review approfondita su claude.ai (marzo 2026).

---

## 1. Dove si trova tutto

| Cosa | Path / URL |
|---|---|
| Repo | `github.com/AronneZanichelli/eu4-assistant` |
| Branch principale | `main` |
| Design doc | `EU4_ASSISTANT_BOT_DESIGN.md` (nella root del repo) |
| Piano M3 | `M3_PLAN.md` (nella root) |
| Package Python | `eu4_assistant_bot/` |
| Test | `tests/` |
| Installazione dev | `pip install -e ".[dev]"` poi `python -m pytest -q` |
| Python supportato | 3.11, 3.12 |

---

## 2. Stato attuale del progetto

### Branch da applicare

**`fix/review-bugfixes`** — NON pushato (mancava PAT nel remote clone).
Contiene 3 bug fix + aggiornamento test. Patch allegata: `fix-review-bugfixes.patch`.

Contenuto della patch:
- **`extractor.py`**: `_extract_military` leggeva `army` dal tree root invece che dal country block. Fix: `tree.get("army")` → `c.get("army")` dove `c = self._country_block(tree, country)`.
- **`config.py`**: Tutti i default `Path.home() / ...` in `AppConfig` erano valutati a import-time (una sola volta). Fix: convertiti in `field(default_factory=lambda: Path.home() / ...)`. Questo risolve sia il bug del `data_dir` relativo (ora punta a `~/.eu4-assistant/`) sia la testabilità.
- **`state_reader.py`**: `SnapshotReadError` aveva `__str__` definito due volte. Rimosso il duplicato.
- **Test aggiornati**: fixture extractor con `army` dentro country block; bootstrap test con `monkeypatch.setattr(Path, "home", ...)` per isolamento.

**Azione:** applicare la patch su main:
```bash
cd eu4-assistant
git checkout main
git am fix-review-bugfixes.patch
```

> **Nota:** il branch remoto `fix/parser-serialization-ci` esiste ancora su GitHub ma i suoi commit sono già tutti in main. Non serve mergiarlo, si può cancellare. Stessa cosa per `fix/ci-python311-compat` e i branch feat.

### Milestone completati

| Milestone | Stato |
|---|---|
| M1 — Foundation (config, models, telemetry, parser PoC, CLI) | ✅ |
| M2 — Decision engine + simulated executor | ✅ |
| M3 — ClausewitzTextParser + SaveUnzipper + ModBuilder | ✅ (nel codice, M3_PLAN.md ha i dettagli) |
| M4 — FileWatcher + StateExtractor + GameSnapshot v2 | ✅ |

### Prossimo milestone: M5

M5 = UI PyQt6 base + PauseController + hotkey F2.
Ma prima di partire con M5, ci sono migliorie strutturali da fare (sezione 4).

---

## 3. Bug e problemi noti (dalla review)

### Critici — da fixare prima di procedere

I primi 3 sono risolti nella patch `fix-review-bugfixes.patch`. I restanti sono ancora aperti:

| # | File | Problema | Stato |
|---|---|---|---|
| 1 | `state_reader.py` | Doppio `__str__` su `SnapshotReadError` | ✅ nella patch |
| 2 | `extractor.py` | `_extract_military` leggeva army dal tree root | ✅ nella patch |
| 3 | `config.py` | `data_dir` relativo + Path.home() valutato a import-time | ✅ nella patch |
| 4 | `parser.py` | Euristica scalar list fallisce su liste di blocchi anonimi (vedi sotto) | ❌ aperto |
| 5 | `state_reader.py` | `SnapshotReader.read_json_snapshot` non gestisce campi M4 (eu4_date, stability, prestige, legitimacy, tech, ideas) | ❌ aperto |
| 6 | `mod/mod_builder.py` | `on_actions` dentro `events/monthly_save.txt` — EU4 vuole `on_actions` in `common/on_actions/`, non nel file eventi | ❌ aperto — validare con il gioco |

### Dettaglio bug #4 — Parser euristica scalar list

Il parser decide se un blocco `{ ... }` è una lista scalare o un blocco annidato cercando `=` prima della prima `}`. Questo fallisce su pattern EU4 tipo:

```
armies = {
    { name = "Army 1" }
    { name = "Army 2" }
}
```

Qui l'euristica vede `{` poi `name` poi `=` → decide "è un blocco annidato" e chiama `_parse_block`. Ma in realtà è una lista di blocchi anonimi. Il risultato sarà un parse tree sbagliato per quei pattern. Fix consigliato: quando il token subito dopo `{` è un altro `{`, trattarlo come lista di blocchi.

---

## 4. Migliorie strutturali — ordinate per milestone

Aronne vuole fare tutto insieme, milestone per milestone. Ecco il piano:

### Pre-M5 (cleanup tecnico)

**A. Refactor parser — eliminare duplicazione**
`parse_text()` (righe 156-196) è un copia-incolla di `_parse_block()`. Soluzione: wrappare il contenuto in un blocco virtuale e chiamare `_parse_block` una volta sola.

**B. Aggiornare `EU4RulesLoader` al parser ricorsivo**
Attualmente usa ancora `_LegacyClausewitzParser` (flat key=value). I file EU4 in `common/units/`, `common/ideas/` ecc. sono annidati. Il loader funziona solo per caso sui file più semplici. Deve usare `ClausewitzTextParser`.

**C. Aggiungere modelli tipizzati mancanti**
Il design doc prevede:
- `ArmyState` (id, location, troops, composition) — attualmente `armies: list[dict[str, Any]]`
- `ProvinceState` (province_id, name, owner, unrest, development, ...) — completamente assente
- `TradeNodeState` (id, our_power, total_value, merchants) — completamente assente
- `merchants_deployed` in `EconomyState` — assente
- `ae_max` in `RiskState` — assente, la coalition risk usa overextension come proxy (impreciso)

**D. `SnapshotReader` — allineare ai campi M4**
`read_json_snapshot` ignora eu4_date, stability, prestige, legitimacy, tech, ideas. Aggiungere parsing per tutti.

### Durante M5

**E. Thread safety watcher**
`_last_change` in `watcher.py` è letto/scritto da thread diversi senza lock. Aggiungere `threading.Lock` per portabilità.

### Durante M6/M7

**F. Decision engine — raccomandazioni contestuali**
Quando nessun rischio è attivo, il fallback restituisce sempre le stesse 3 raccomandazioni statiche. Dovrebbe considerare tech gap, MP accumulati, colonisti liberi, ecc.

**G. Validazione mod EU4**
Il file `on_actions` nel `monthly_save.txt` potrebbe non essere registrato da EU4 (vedi bug #6). Testare con il gioco e, se necessario, splittare in `events/monthly_save.txt` + `common/on_actions/eu4_assistant.txt`.

**H. `SaveUnzipper` — validazione plain text**
Se il file non è ZIP, viene letto come testo senza alcun check. Un file binario arbitrario verrebbe accettato. Aggiungere un check minimo (presenza di `=` o `{`).

---

## 5. Architettura — cose da sapere

### Pipeline dati
```
autosave.eu4 → FileWatcher (watchdog, debounce 500ms)
             → SaveUnzipper (ZIP o plain text)
             → ClausewitzTextParser (tokenizer + parser ricorsivo → dict Python)
             → StateExtractor (dict → GameSnapshot tipizzato, parsing difensivo)
             → DecisionEngine (risk alerts + top-3 raccomandazioni)
             → UI (PyQt6, M5)
```

### Convenzioni codice
- `from __future__ import annotations` in tutti i file
- `@dataclass(slots=True)` ovunque (tranne dove serve ereditarietà)
- Parsing difensivo: ogni campo ha default safe, mai eccezioni su dati mancanti
- Chiavi duplicate nel parser → automaticamente convertite in `list`
- I test usano `tmp_path` e `monkeypatch` di pytest, niente file system reale

### Dipendenze
- `watchdog>=4.0,<7.0` — file watching
- `pytest>=7.0` — dev only
- Tutto il resto è stdlib Python

### CI
Il workflow GitHub Actions testa su Python 3.11 e 3.12 con `pip install -e ".[dev]"` + `pytest`.

---

## 6. File di test e fixture

### Save file reali
Aronne ha save file EU4 reali disponibili. Quando serve testare il parser su dati veri, chiedigli di fornirli. I save sono ZIP contenenti `gamestate` (testo Clausewitz), `meta`, e `ai`.

### Fixture esistenti
- `tests/fixtures/sample_flat.eu4.txt` — save minimale flat
- `tests/fixtures/sample_nested.eu4.txt` — save con blocchi annidati

### Fixture mancanti (dal piano M3, mai create)
- `sample_large.eu4.txt` — 2000+ righe per test performance
- `sample_save.eu4` — ZIP con gamestate minimale

---

## 7. Roadmap rimanente

| Milestone | Contenuto | Dipendenze |
|---|---|---|
| **M5** | UI PyQt6 (Dashboard + Advisor + Log) + PauseController + hotkey F2 | M4 |
| **M6** | Military logic reale (stack scoring, army advisor, wartime routing) | M4, M5 |
| **M7** | Colonial + Economy logic reale | M4, M5 |
| **M8** | ActionExecutor reale (pyautogui) + semi-bot + full-bot params UI | M5, M6, M7 |
| **M9** | QA end-to-end, stabilità, crash hardening, DLC regression | tutti |
| **M10** | Packaging PyInstaller + changelog + docs | M9 |

Dettagli completi di ogni milestone nel design doc `EU4_ASSISTANT_BOT_DESIGN.md`.

---

## 8. Note per Claude Code

- Il repo si clona con `git clone https://github.com/AronneZanichelli/eu4-assistant.git`
- Per pushare serve un PAT con scope `workflow` nel remote URL
- `api.github.com` è bloccato dall'ambiente Claude — le PR vanno create manualmente da Aronne su GitHub
- Prima di qualsiasi modifica: `pip install -e ".[dev]"` e `python -m pytest -q` per verificare che tutto parta verde
- Il design doc è la fonte di verità per le specifiche. Se qualcosa nel codice diverge dal doc, il doc ha ragione (a meno che Aronne non dica diversamente)
- La lingua dell'UI e dei messaggi utente è italiano. Il codice (variabili, commenti, commit) è in inglese.
