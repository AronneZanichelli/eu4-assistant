# Code Review — EU4 Assistant + Bot

**Data:** 2026-06-23
**Commit revisionato:** `65929fd` (main)
**Metodo:** gsd map-codebase (4 mapper paralleli) + verifica manuale diretta sul codice (stile superpowers: ogni claim ricontrollato su file:riga prima di asserirlo).
**Ambito:** intero package `eu4_assistant_bot/` (3288 LOC) + test + CI.

---

## Sintesi findings

| ID | Severità | Area | Sintesi |
|----|----------|------|---------|
| C1 | 🔴 CRITICAL | live-watch | `main.py:201` chiama `parse()` inesistente → feature live rotta |
| H1 | 🟠 HIGH | integrazione | PauseController + HotkeyManager implementati ma non cablati |
| H2 | 🟠 HIGH | error handling | `except (SaveFormatError, Exception)` maschera bug di programmazione |
| M1 | 🟡 MED | sicurezza/bot | `execute()` SEMI/FULL_BOT senza gate di conferma; FULL_BOT è stub |
| M2 | 🟡 MED | compat | drift versioni Python: codice gira su 3.14, CI/classifier dichiarano 3.11/3.12 |
| M3 | 🟡 MED | portabilità | `pynput` import top-level in `ui/hotkey.py` (rompe import su Linux/3.14) |
| L1 | 🟢 LOW | coerenza | meccanismo pausa: executor usa `space`, design cita F1 |
| L2 | 🟢 LOW | tech debt | alias deprecato `ClausewitzParser` (DeprecationWarning nei test) |
| L3 | 🟢 LOW | igiene git | 8 branch remoti stale (feat/* fix/* mergiati mar 2026) |
| L4 | 🟢 LOW | doc | versione 0.5.0 vs "v1.0"; CHANGELOG M1–M10 vs commit M11/M12; "Advisor" vs `assist` |
| G1 | ⚪ GAP | test | nessun test di integrazione su `run_with_ui()`/`_process_save` (causa di C1) |

---

## Dettaglio

### C1 — 🔴 CRITICAL: feature live-watch rotta
**Dove:** `eu4_assistant_bot/main.py:201`
```python
tree = ClausewitzTextParser().parse(gamestate_text)
```
**Problema:** `ClausewitzTextParser` definisce `parse_text()` (`parser.py:182`) e `parse_file()` (`parser.py:191`), **non** `parse()`. Ogni autosave solleva `AttributeError`. La modalità live (`--watch`, il valore principale del prodotto) non produce mai snapshot.
**Perché è sfuggito:** l'eccezione è ingoiata da H2 e nessun test copre questo path (G1).
**Fix:** `ClausewitzTextParser().parse_text(gamestate_text)` (oppure aggiungere un alias `parse = parse_text`). Aggiungere test di integrazione (G1).

### H1 — 🟠 HIGH: componenti non cablati
**Dove:** `eu4_assistant_bot/pause_controller.py`, `eu4_assistant_bot/ui/hotkey.py`
**Problema:** `PauseController` e `HotkeyManager` sono completi e testati ma non istanziati in `main.py`/`MainWindow` (in `main_window.py` "hotkey" compare solo nei commenti, righe 4 e 190). Auto-pausa su ribelli/guerra e toggle globale F2 **non funzionano end-to-end**.
**Fix:** cablare in `run_with_ui()`; oppure documentare esplicitamente come deferred.

### H2 — 🟠 HIGH: error handling che maschera bug
**Dove:** `eu4_assistant_bot/main.py:203`
```python
except (SaveFormatError, Exception) as exc:
```
**Problema:** `(SaveFormatError, Exception)` è ridondante (`Exception` copre già `SaveFormatError`) e troppo ampio: cattura `AttributeError`/`KeyError`/bug di programmazione e li declassa a "Errore parsing save". Ha nascosto C1 per mesi.
**Fix:** catturare solo `SaveFormatError` (+ eventuali errori di parsing attesi); lasciar propagare l'inatteso o loggarlo con stacktrace (`logger.exception`).
**Nota:** gli altri 5 `except` larghi del codebase sono marcati `# noqa: BLE001` in contesti difendibili (thread listener, telemetry) — accettabili.

### M1 — 🟡 MED: azioni bot senza conferma
**Dove:** `eu4_assistant_bot/executor.py` (`execute()`, righe ~77–119; `FULL_BOT` riga 85)
**Problema:** nel path reale per `SEMI_BOT`/`FULL_BOT` non c'è gate di conferma (il check `requires_confirmation` è solo in `simulate()`/ASSIST). Oggi l'azione reale si limita a `pyautogui.press("space")` (rischio basso) e `FULL_BOT == SEMI_BOT` (stub M8), ma serve un gate di conferma **prima** di espandere ad azioni reali (navigazione menu, click).
**Fix:** richiedere conferma esplicita per azioni reali con `requires_confirmation` anche fuori da ASSIST.

### M2 — 🟡 MED: drift versioni Python
**Problema:** il codice gira su Python **3.14** (venv locale, 132 test verdi), ma `pyproject.toml` ha `requires-python>=3.11`, i `classifiers` elencano solo 3.11/3.12 e la matrice CI (`.github/workflows/ci.yml`) testa solo 3.11/3.12.
**Fix:** aggiungere 3.13/3.14 alla matrice CI e ai classifier, oppure dichiarare esplicitamente il supporto.

### M3 — 🟡 MED: import non portabile
**Dove:** `eu4_assistant_bot/ui/hotkey.py:9`
```python
from pynput.keyboard import Key, Listener
```
**Problema:** import top-level di `pynput` → importare il modulo fallisce dove `pynput`/`evdev` non sono disponibili (Linux + Python 3.14: `evdev` non ha wheel e richiede kernel headers). Impatto attuale basso perché il modulo è non cablato (H1), ma morderà appena lo si cabla su una dev box non-Windows.
**Fix:** import lazy dentro i metodi, come già fa `executor.py:133` per `pyautogui` (`# noqa: PLC0415`).

### L1 — 🟢 LOW: meccanismo pausa incoerente
`executor.py:141` invia `space` (`reason="game_paused_via_space"`); il design/README citano F1 per la pausa automatica; `pause_controller.py` è un componente separato. Riconciliare la strategia di pausa (Space è il toggle pausa di EU4; F1 apre un menu).

### L2 — 🟢 LOW: alias deprecato
`ClausewitzParser` è un alias deprecato che emette `DeprecationWarning` (visibile in `tests/test_parser.py:156`). Pianificare la rimozione.

### L3 — 🟢 LOW: branch remoti stale
8 branch su origin mergiati a marzo 2026 mai cancellati (`feat/m3-*`, `feat/m4-*`, `feat/m5-*`, `fix/ci-*`, `fix/parser-*`, `claude/*`, `AronneZanichelli-patch-1`). Prune consigliato.

### L4 — 🟢 LOW: incoerenze documentali
Versione `0.5.0` (pyproject) vs "v1.0 (definitiva)" (design doc); CHANGELOG documenta M1–M10 mentre git ha commit M11/M12; label "Advisor" (SPEC) vs token CLI/enum `assist`. Allineare. (Vedi anche `.planning/INGEST-CONFLICTS.md`.)

### G1 — ⚪ GAP: copertura del path live
Nessun test di integrazione esercita `run_with_ui()` / `_process_save()`. È la ragione per cui C1 è passato inosservato nonostante 132 test verdi. Aggiungere un test che faccia passare un gamestate di esempio attraverso unzip→parse→extract→engine.

---

## Aspetti positivi

- **Stile pulito:** zero `TODO/FIXME/HACK`, zero `print` di debug, nessun mutable default arg.
- **Modellazione:** `@dataclass(slots=True)` + `field(default_factory=...)`; enum `str`-mixin via preset in `config.py`; type hints PEP 585/604 con `from __future__ import annotations`.
- **Errori:** eccezioni custom per-modulo con `raise ... from exc`.
- **Dipendenze opzionali:** import lazy con fallback graceful (pattern corretto in `executor.py`).
- **Test:** 132 test, dependency-injection invece di mock; pattern Qt offscreen.
- **Sicurezza:** offline (zero librerie network/DB/auth), `pip-audit` pulito sul subset installato, nessun secret nel repo.

---

## Stato salute (verificato 2026-06-23)

- `pip install -e .[dev]` su Linux/Py3.14 **fallisce** per `evdev` (dep transitiva di `pynput`, no wheel + kernel headers mancanti). Workaround usato: install senza `pynput` (core + pytest + PyQt6 6.11). Su Windows non si presenta.
- `QT_QPA_PLATFORM=offscreen pytest` → **132 passed**, 1 warning (L2).
- CI (`ci.yml`) verde su 3.11/3.12; `build.yml` produce l'exe Windows su tag `v*`.

---

## Prossimi passi consigliati (in ordine)

1. **C1 + H2 + G1** insieme: fix `parse_text`, restringere l'except, aggiungere il test di integrazione del path live. (Un solo fix sblocca il valore principale del prodotto.)
2. **H1:** cablare PauseController + HotkeyManager in `run_with_ui()`.
3. **M1:** gate di conferma per le azioni reali SEMI/FULL_BOT.
4. **M2 + M3:** allineare matrice CI a 3.13/3.14 e rendere lazy l'import pynput.
5. **L3 + L4:** prune branch stale, allineare versione/CHANGELOG/naming.
