# Codex Task — M3: ClausewitzTextParser, SaveUnzipper, Mod autosave

## Contesto

Questo repo contiene `eu4_assistant_bot`, un companion Python per Europa Universalis IV.
M1 e M2 sono completati. Questo task implementa M3 interamente.

Il file `EU4_ASSISTANT_BOT_DESIGN.md` contiene la progettazione completa del progetto.
Il file `M3_PLAN.md` contiene il piano dettagliato di questo milestone.

---

## Obiettivo

Implementare tre componenti:

1. **`ClausewitzTextParser`** ricorsivo completo in `eu4_assistant_bot/parser.py`
2. **`SaveUnzipper`** in `eu4_assistant_bot/save_unzipper.py`
3. **Mod autosave mensile** con `ModBuilder` in `eu4_assistant_bot/mod/`

Al termine, il sistema deve essere in grado di aprire un file `autosave.eu4` reale
(ZIP contenente testo Clausewitz) e restituire un albero Python navigabile.

---

## Task 1 — ClausewitzTextParser (riscrittura `parser.py`)

### Sostituisci `ClausewitzParser` con `ClausewitzTextParser`

Il parser deve supportare l'intera grammatica Clausewitz testuale di EU4:

```
# scalari
key = value
key = "quoted string"
key = 1444.11.11
key = yes
key = no
key = 42
key = 3.14

# blocco annidato
key = {
    inner = value
    nested = { deep = 1 }
}

# lista di scalari
key = { a b c }
key = { 1 2 3 }

# lista di blocchi (chiave ripetuta stesso parent)
army = { name = "First" }
army = { name = "Second" }

# blocco vuoto
key = { }

# commenti
# commento a riga intera
key = value # commento inline (ignorato)
```

**Regole di tipizzazione output:**
- `yes` / `no` → `bool`
- stringa numerica intera → `int`
- stringa numerica decimale → `float`
- pattern `YYYY.MM.DD` → `str` (conservato as-is)
- tutto il resto → `str` (senza virgolette)

**Regola chiavi duplicate:**
- Se una chiave appare più volte nello stesso blocco, il suo valore nel dict
  diventa una `list` contenente tutti i valori in ordine di apparizione.
- Esempio: `army = {...}` ripetuto 3 volte → `{"army": [{...}, {...}, {...}]}`

**API pubblica:**
```python
class ClausewitzTextParser:
    def parse_text(self, text: str) -> dict[str, Any]: ...
    def parse_file(self, path: Path) -> dict[str, Any]: ...
```

**Backward compatibility:**
- Rinomina la classe esistente `ClausewitzParser` in `_LegacyClausewitzParser`
- Aggiungi alias deprecato: `ClausewitzParser = _LegacyClausewitzParser`
- `EU4RulesLoader` continua a usare `_LegacyClausewitzParser` internamente
  (verrà aggiornato in M4 — non farlo ora)
- I test esistenti in `tests/test_parser.py` devono continuare a passare

**Vincoli:**
- Solo stdlib Python (no dipendenze esterne)
- Encoding: `utf-8` con `errors="replace"` per file letti da disco
- Nessuna eccezione non gestita per input malformati: restituisci quello che riesci
  a parsare, ignora righe non riconoscibili

---

## Task 2 — SaveUnzipper (nuovo file `save_unzipper.py`)

```python
class SaveFormatError(Exception): ...

class SaveUnzipper:
    def extract_gamestate(self, path: Path) -> str:
        """
        Apre un file .eu4 e restituisce il contenuto testuale del gamestate.

        - Se il file inizia con i magic bytes ZIP (b'PK'):
            apre come ZIP, cerca un entry chiamato 'gamestate' (o il primo
            entry non chiamato 'meta'), e ne restituisce il contenuto decodificato.
        - Se il file è testo plain (non ZIP):
            lo legge direttamente e lo restituisce.
        - Se il file non esiste → SaveFormatError
        - Se il ZIP non contiene 'gamestate' → SaveFormatError
        - Se il file è corrotto → SaveFormatError
        """
```

**Note:**
- I save EU4 normali sono ZIP con tre entry: `meta`, `gamestate`, `ai`
- Il gamestate è il file principale con lo stato della partita
- Usa `zipfile.ZipFile` dalla stdlib
- Decoding: `utf-8` con `errors="replace"`

---

## Task 3 — ModBuilder (nuovo package `eu4_assistant_bot/mod/`)

Struttura:
```
eu4_assistant_bot/mod/
├── __init__.py          (esporta ModBuilder, ModInstallResult)
└── mod_builder.py
```

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class ModInstallStatus(str, Enum):
    INSTALLED = "installed"
    UPDATED = "updated"
    SKIPPED = "skipped"

@dataclass
class ModInstallResult:
    status: ModInstallStatus
    mod_path: Path
    version: str

class ModBuilder:
    MOD_NAME = "eu4_assistant_autosave"
    
    def install(self, mod_folder: Path, eu4_version: str = "1.37.*") -> ModInstallResult:
        """
        Installa la mod nella cartella mod EU4.
        
        - Crea `mod_folder/eu4_assistant_autosave/` se non esiste
        - Scrive il file .mod e l'evento mensile
        - Se la mod esiste già con la stessa versione → SKIPPED
        - Se la mod esiste con versione diversa → sovrascrive → UPDATED
        - Se la mod non esiste → INSTALLED
        """
```

**Contenuto file mod da generare (hardcoded come stringhe, no Jinja):**

`{mod_folder}/eu4_assistant_autosave.mod`:
```
name = "EU4 Assistant - Monthly Autosave"
supported_version = "{eu4_version}"
path = "mod/eu4_assistant_autosave"
```

`{mod_folder}/eu4_assistant_autosave/events/monthly_save.txt`:
```
namespace = eu4_assistant

country_event = {
    id = eu4_assistant.1
    hidden = yes
    is_triggered_only = yes

    option = {
        name = eu4_assistant.1.a
    }
}

on_actions = {
    on_monthly_pulse = {
        events = { eu4_assistant.1 }
    }
}
```

---

## Task 4 — Test suite

### `tests/test_parser.py` — rimpiazza il file esistente

Casi obbligatori:

```python
# scalari
test_parse_integer()
test_parse_float()
test_parse_bool_yes_no()
test_parse_quoted_string()
test_parse_date_string()

# strutture
test_parse_nested_block()
test_parse_deep_nested_block()         # ≥ 3 livelli
test_parse_scalar_list()               # { a b c }
test_parse_repeated_key_becomes_list() # chiave duplicata → list
test_parse_empty_block()               # key = { }

# robustezza
test_parse_ignores_comments()
test_parse_inline_comment()
test_parse_empty_string()
test_parse_only_comments()
test_parse_non_ascii_values()          # caratteri accentati nei nomi

# file
test_parse_file(tmp_path)
```

### `tests/test_save_unzipper.py` — nuovo file

```python
test_extract_from_valid_zip(tmp_path)     # ZIP con entry 'gamestate'
test_extract_from_plain_text(tmp_path)    # file testo non-ZIP
test_raises_on_missing_file(tmp_path)
test_raises_on_zip_without_gamestate(tmp_path)
test_raises_on_corrupted_file(tmp_path)
```

### `tests/test_mod_builder.py` — nuovo file

```python
test_install_creates_mod_files(tmp_path)
test_install_returns_installed_status(tmp_path)
test_install_idempotent_same_version(tmp_path)   # seconda chiamata → SKIPPED
test_install_updates_different_version(tmp_path) # versione nuova → UPDATED
test_install_creates_missing_directory(tmp_path)
test_generated_mod_file_contains_version(tmp_path)
test_generated_event_file_contains_namespace(tmp_path)
```

### Fixtures `tests/fixtures/`

Crea questi file di fixture (contenuto minimale ma realistico):

**`sample_flat.eu4.txt`:**
```
date = 1460.06.01
player = "POR"
speed = 3
multi_player = no
```

**`sample_nested.eu4.txt`:**
```
date = 1460.06.01
player = "POR"
countries = {
    POR = {
        treasury = 120.500
        manpower = 22.000
        technology = {
            adm_tech = 4
            dip_tech = 4
            mil_tech = 4
        }
    }
}
army = {
    name = "Exercito"
    location = 1297
}
army = {
    name = "Guarda"
    location = 230
}
```

**`sample_save.eu4`** — crea un ZIP valido in-memory con entry `gamestate`
contenente il testo di `sample_nested.eu4.txt`. Genera questo file
programmaticamente nello script di setup dei test oppure come conftest.py fixture.

---

## Vincoli globali

1. `python -m pytest -q` deve passare al 100% dopo le modifiche
2. Nessuna dipendenza esterna aggiunta (solo stdlib)
3. Tutti i file nuovi hanno type hints completi e docstring sulla classe
4. Nessun breaking change su interfacce pubbliche esistenti
5. Il file `parser.py` deve conservare il PoC `ClausewitzParser` come alias deprecato

---

## Checklist di completamento

- [ ] `ClausewitzTextParser.parse_text()` e `parse_file()` implementati
- [ ] `SaveUnzipper.extract_gamestate()` implementato
- [ ] `ModBuilder.install()` implementato
- [ ] Tutti i test in `test_parser.py` passano
- [ ] Tutti i test in `test_save_unzipper.py` passano
- [ ] Tutti i test in `test_mod_builder.py` passano
- [ ] Test esistenti (M1 + M2) continuano a passare
- [ ] Nessuna dipendenza esterna aggiunta
