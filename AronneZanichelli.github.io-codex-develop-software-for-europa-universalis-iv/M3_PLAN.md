# M3 — Piano implementazione

## Obiettivo

Sostituire il parser PoC con un `ClausewitzTextParser` ricorsivo completo,
aggiungere `SaveUnzipper` per la decompressione dei save file EU4, e produrre
la mod di autosave mensile. Al termine di M3, il sistema è in grado di leggere
un file `autosave.eu4` reale e restituire un albero Python navigabile.

---

## Contesto: cosa esiste già

| File | Stato | Note |
|---|---|---|
| `eu4_assistant_bot/parser.py` | PoC — solo flat key=value | Da sostituire con parser ricorsivo |
| `eu4_assistant_bot/save_adapter.py` | Lavora su formato custom (extract) | Rimane invariato per ora |
| `tests/test_parser.py` | 2 test su PoC | Da espandere radicalmente |

---

## Grammatica Clausewitz da supportare

Il formato testuale EU4 ha queste strutture fondamentali:

```
# 1. Coppia chiave = valore scalare
key = value
key = "quoted string"
key = 1444.11.11          # data
key = yes                 # booleano

# 2. Blocco annidato
key = {
    inner_key = value
    nested = {
        deep = 42
    }
}

# 3. Lista di valori (no chiave interna)
key = { value1 value2 value3 }
key = { 10 20 30 }

# 4. Chiave ripetuta → lista di blocchi
army = { ... }
army = { ... }            # stesso parent, stessa chiave → list

# 5. Commenti
# questo è un commento
```

Casi edge critici per i save EU4:
- Valori con `=` nel testo (es. stringhe di eventi)
- Blocchi vuoti: `key = { }`
- Date come chiavi: `1444.11.11 = { ... }`
- Encoding: UTF-8 con `errors="replace"` per caratteri speciali nei nomi

---

## Deliverable M3

### 1. `eu4_assistant_bot/parser.py` — riscrittura completa

**`ClausewitzTextParser`** (sostituisce il PoC):
- Tokenizer che converte il testo in stream di token: `KEY`, `EQUALS`, `OPEN_BRACE`, `CLOSE_BRACE`, `VALUE`
- Parser ricorsivo che costruisce un albero `dict[str, Any]`
- Chiavi duplicate nello stesso blocco → convertite automaticamente in `list`
- Tipi Python nativi: `int`, `float`, `bool` (yes/no), `str`, data come `str` (`"1444.11.11"`)
- Gestisce file di qualsiasi dimensione in modo efficiente (no caricamento intero in memoria per file >30MB: parsing riga per riga con stato)

**`SaveUnzipper`** (nuovo):
- Riceve il path di un `.eu4`
- Rileva se è un ZIP (magic bytes `PK`)
- Se ZIP: estrae il file `gamestate` (il principale) e lo restituisce come `str`
- Se testo plain: lo legge direttamente
- Solleva `SaveFormatError` se il file non è riconoscibile

**`EU4RulesLoader`** (aggiornato):
- Usa il nuovo `ClausewitzTextParser` al posto del PoC
- Interfaccia pubblica invariata (nessun breaking change)

**Conservazione backward compatibility:**
- La classe `ClausewitzParser` (PoC) viene rinominata `_LegacyClausewitzParser` e deprecata con warning
- I test esistenti continuano a passare

---

### 2. `eu4_assistant_bot/mod/` — mod autosave mensile (nuovo)

```
eu4_assistant_bot/mod/
├── __init__.py
├── mod_builder.py          ← genera i file della mod nella cartella mod EU4
└── templates/
    ├── eu4_assistant_autosave.mod.j2
    └── monthly_save.txt.j2
```

**Contenuto mod generata:**

`eu4_assistant_autosave.mod`:
```
name = "EU4 Assistant - Monthly Autosave"
supported_version = "1.37.*"
path = "mod/eu4_assistant_autosave"
```

`events/monthly_save.txt`:
```
namespace = eu4_assistant

country_event = {
    id = eu4_assistant.1
    hidden = yes
    is_triggered_only = yes
    option = { name = eu4_assistant.1.a }
}

on_actions = {
    on_monthly_pulse = {
        events = { eu4_assistant.1 }
    }
}
```

`ModBuilder.install(mod_folder: Path, eu4_version: str)`:
- Scrive i file della mod nella cartella mod EU4
- Aggiorna `supported_version` con la versione passata
- Idempotente: se la mod esiste già e la versione è la stessa, non sovrascrive
- Restituisce `ModInstallResult` con path e stato (installed / updated / skipped)

---

### 3. `tests/` — suite estesa

**`tests/test_parser.py`** — casi da coprire:
- Flat key=value (int, float, bool, string, date, quoted string)
- Blocco annidato singolo livello
- Blocco annidato multi-livello (≥3 livelli)
- Lista di valori scalari
- Lista di blocchi (chiave ripetuta → list automatica)
- Blocco vuoto `key = { }`
- Commenti inline e a riga intera
- Data come chiave del blocco
- File vuoto
- File con solo commenti
- Encoding: caratteri non-ASCII in nomi (es. nomi di paesi)
- File grande simulato (>1000 righe)

**`tests/test_save_unzipper.py`** — casi da coprire:
- ZIP valido contenente file `gamestate`
- File testo plain (non ZIP)
- ZIP senza file `gamestate` → `SaveFormatError`
- File corrotto (non ZIP, non testo EU4) → `SaveFormatError`
- File inesistente → `SaveFormatError`

**`tests/test_mod_builder.py`** — casi da coprire:
- Installazione da zero
- Idempotenza (seconda installazione, stessa versione)
- Aggiornamento versione (versione diversa → sovrascrive)
- Cartella mod target non esistente → viene creata

**`tests/fixtures/`** — fixture di test:
- `sample_flat.eu4.txt` — save minimale flat
- `sample_nested.eu4.txt` — save con blocchi annidati realistici (country, army, province)
- `sample_large.eu4.txt` — 2000 righe per test performance
- `sample_save.eu4` — ZIP con gamestate testuale minimale

---

## Struttura file finale dopo M3

```
eu4_assistant_bot/
├── __init__.py
├── config.py
├── decision_engine.py
├── executor.py
├── main.py
├── models.py
├── mod/
│   ├── __init__.py
│   ├── mod_builder.py
│   └── templates/
│       ├── eu4_assistant_autosave.mod.j2
│       └── monthly_save.txt.j2
├── parser.py               ← riscritto
├── save_adapter.py
├── save_unzipper.py        ← nuovo
├── state_reader.py
├── telemetry.py
└── main.py

tests/
├── test_bootstrap.py
├── test_config.py
├── test_decision_engine.py
├── test_executor.py
├── test_mod_builder.py     ← nuovo
├── test_parser.py          ← esteso
├── test_save_adapter.py
├── test_save_unzipper.py   ← nuovo
├── test_state_reader.py
└── fixtures/
    ├── sample_flat.eu4.txt
    ├── sample_nested.eu4.txt
    ├── sample_large.eu4.txt
    └── sample_save.eu4
```

---

## Vincoli e note implementative

1. **Nessun breaking change** su interfacce pubbliche esistenti — M4 e oltre dipendono da M3 senza dover aggiornare codice.
2. **Nessuna dipendenza esterna nuova** — il parser deve usare solo stdlib Python. `zipfile` è già stdlib.
3. **Performance:** il parser deve completare un save da 30MB in <5 secondi su hardware normale.
4. **Encoding:** tutti i file letti con `encoding="utf-8", errors="replace"` per robustezza.
5. **Chiavi duplicate:** la gestione list-automatica è fondamentale — EU4 usa massicciamente chiavi ripetute (es. `army`, `province`, `active_idea_groups`).
6. **Il PoC `ClausewitzParser`** rimane nel file ma deprecato, per non rompere `EU4RulesLoader` prima che M4 lo aggiorni completamente.

---

## Definizione di "Done" per M3

- [ ] `ClausewitzTextParser` parsifica correttamente tutti i casi della grammatica
- [ ] `SaveUnzipper` estrae il gamestate da un `.eu4` reale
- [ ] `EU4RulesLoader` usa il nuovo parser senza breaking change
- [ ] Mod autosave mensile generabile da `ModBuilder.install()`
- [ ] Suite test: tutti i test passano con `python -m pytest -q`
- [ ] Nessuna dipendenza esterna aggiunta
- [ ] Performance: save 30MB parsato in <5s
