# EU4 Assistant + Bot — Progettazione v1.0 (definitiva)

## 1. Obiettivo del progetto

Applicazione desktop Windows che si affianca a Europa Universalis IV in tempo quasi-reale, con tre modalità operative selezionabili durante la sessione di gioco.

> **Scope v1.0:** campagne normali con tutti i DLC attivi, mod grafiche/QoL compatibili. Ironman escluso. Obiettivo primario: stabilità completa dall'inizio alla fine di una campagna, zero crash.

---

## 2. Contesto d'uso

| Parametro | Valore |
|---|---|
| Monitor | 2 — EU4 su monitor principale (fullscreen borderless, 2560x1440), companion su secondo monitor |
| Versione EU4 | Sempre l'ultima (auto-update), installata via Steam |
| DLC | Tutti attivi |
| Mod | Grafiche / QoL + mod parziale traduzione IT (non modifica meccaniche) |
| Lingua EU4 | Inglese (con mod traduzione parziale IT) |
| Lingua UI companion | Italiano |
| Tema | Scuro (coerente con EU4) |

---

## 3. Modalità operative e flusso UX

Il sistema ha **una sola modalità attiva per volta**, selezionabile tramite controlli in UI.

### 3.1 Advisor (default)
- L'app legge il save, analizza lo stato e mostra raccomandazioni + alert.
- **Nessuna azione automatica.**
- Ogni raccomandazione ha un pulsante **"Esegui"** per delegare quella singola azione al bot.

### 3.2 Semi-bot (per singola azione)
- Attivato cliccando "Esegui" su una raccomandazione specifica.
- L'app mostra un dialog di conferma con dettaglio dell'azione prima di procedere.
- Dopo l'esecuzione torna automaticamente in modalità Advisor.

### 3.3 Full-bot (switch globale)
- Uno switch dedicato in UI attiva la modalità full-bot.
- Prima dell'attivazione appare un pannello parametri configurabili (budget, limiti, priorità, modalità colonial bot).
- Il bot gestisce in autonomia le categorie abilitate, entro i guardrail impostati.
- Uno switch visibile e sempre accessibile permette di disattivarlo istantaneamente.
- I parametri configurati vengono **salvati tra sessioni**.

---

## 4. Funzionalità per priorità

| Priorità | Area | Descrizione |
|---|---|---|
| 1 | **Advisor** | Raccomandazioni contestuali top-3 con spiegazione, alert rischio in tempo reale |
| 2 | **Colonial bot** | Ranking province, gestione invio coloni, ottimizzazione budget coloniale |
| 3 | **Military bot** | Composizione stack, reclutamento, movement, assedi, ritirata/ingaggio in guerra. Trattative di pace sempre approvate dal giocatore. |
| 4 | **Economy advisor** | Steering mercanti, ottimizzazione tech timing, gestione budget |

---

## 5. Comportamenti automatici

### 5.1 Pausa automatica EU4
L'app invia `F1` (tasto pausa EU4) automaticamente quando rileva:
- **Ribellione imminente** — unrest massimo in una o più province
- **Guerra dichiarata** — un paese ha dichiarato guerra al giocatore

> Funzionalità presente ma non critica per l'utente — implementata con bassa priorità, non deve impattare stabilità.

### 5.2 Hotkey
- `F2` (configurabile) — mostra/nasconde la finestra companion sul secondo monitor

### 5.3 Persistenza tra sessioni
- Modalità attiva al momento della chiusura
- Parametri full-bot configurati
- Changelog mostrato al primo avvio dopo un aggiornamento

### 5.4 Gestione errori del bot
Quando il bot fallisce un'azione (pre-check negativo, post-check mismatch, eccezione):

**Classificazione errori:**
- **Critico** — azione eseguita ma con effetto sbagliato, stato di gioco potenzialmente alterato → bot si ferma, notifica visiva + suono, attende conferma esplicita "Riprendi" prima di continuare.
- **Minore** — azione non eseguita (es. elemento UI non trovato in pre-check) → bot si ferma, notifica visiva + suono, riprende automaticamente al prossimo autosave.

**Notifica errore:** banner rosso in cima all'UI con descrizione dell'errore, audio alert, badge sul log. Il bot entra in stato `errore` (distinto da `pausa` e `off`).

### 5.5 Stati del full-bot
Il full-bot ha tre stati distinti, sempre visibili in UI:

| Stato | Icona | Comportamento |
|---|---|---|
| **Attivo** | ● verde | Esegue azioni in autonomia |
| **In pausa** | ⏸ giallo | Monitora ma non esegue, riprende con un click |
| **Errore** | ✕ rosso | Fermo per errore, riprende solo dopo conferma (se critico) o automaticamente (se minore) |
| **Off** | ○ grigio | Disattivato, solo advisor passivo |

---

## 6. Vincoli tecnici e scelte progettuali

### 6.1 Sorgente dati: autosave file watching

EU4 non espone API esterne. L'unico canale di lettura affidabile è il **file autosave**.

- Un file watcher (`watchdog`) monitora `autosave.eu4` nella cartella documenti Paradox.
- Una **mod leggera** forza il salvataggio ogni mese in-game (compatibile achievement).
- Ad ogni modifica del file: parsing → extraction → decision → aggiornamento UI.
- Latenza attesa: **1–3 secondi** dal salvataggio all'UI aggiornata.

### 6.2 Formato save EU4

I save file sono in formato **Clausewitz testuale** compressi in ZIP.

- Parser custom Python ricorsivo per testo Clausewitz completo.
- `SaveUnzipper` gestisce la decompressione ZIP pre-parsing.
- Ironman (binary Clausewitz) è fuori scope per v1.0.

### 6.3 Compatibilità DLC

I DLC aggiungono meccaniche che modificano la struttura del save (estates, parliaments, fervor, harmonization, ecc.). Strategia:

- **Parsing difensivo:** ogni campo ha un valore di default safe se assente.
- **Nessuna assunzione su sezioni opzionali:** estratte se presenti, ignorate se assenti.
- **Graceful degradation:** se una sezione DLC non è parsata, l'advisor mostra i dati disponibili senza crashare.
- **Test su sample save:** suite di test con save campione da diverse combinazioni DLC.

### 6.4 UI: finestra dedicata sul secondo monitor (PyQt6)

Finestra standard (non overlay) sul secondo monitor. PyQt6 scelto per:
- Widget nativi Windows, rendering fluido
- Controllo completo su tema scuro e layout
- Packaging agevole con PyInstaller

La finestra ricorda posizione e dimensioni tra sessioni.

### 6.5 Esecuzione azioni (Semi/Full-bot)

Azioni via `pyautogui` + `win32api`. Template matching basato su elementi UI inglesi (lingua base EU4), non sul testo tradotto dalla mod — in questo modo la mod di traduzione non interferisce con il riconoscimento UI. Ogni azione:
- Verifica pre-esecuzione (template matching screenshot region)
- Esecuzione click/tastiera
- Verifica post-esecuzione (conferma effetto atteso)
- Fallback con log in caso di mismatch

### 6.6 Rilevamento automatico percorsi

Al primo avvio, l'app cerca automaticamente:
- Cartella installazione EU4 (Steam: `steamapps/common/Europa Universalis IV`)
- Cartella documenti Paradox (`Documents/Paradox Interactive/Europa Universalis IV`)
- Se non trovati, mostra dialog di selezione manuale.

---

## 7. Architettura v1.0

```
┌──────────────────────────────────────────────────────────────┐
│                   UI Layer (PyQt6) — secondo monitor         │
│                                                              │
│  ┌────────────┐  ┌─────────────────────┐  ┌──────────────┐  │
│  │ Dashboard  │  │ Advisor             │  │ Log feed     │  │
│  │ stato live │  │ top-3 + [Esegui]    │  │ eventi+alert │  │
│  └────────────┘  └─────────────────────┘  └──────────────┘  │
│                                                              │
│  [ Advisor | Semi-bot | ◉ Full-bot ] ← modalità switch      │
│  [ F2: mostra/nascondi ]  [ ⏸ pausa auto ]                  │
└──────────────────────────────────────────────────────────────┘
                            ↕ QSignals
┌──────────────────────────────────────────────────────────────┐
│                     Core Pipeline                            │
│  FileWatcher → SaveUnzipper → ClausewitzParser               │
│       → StateExtractor → GameSnapshot                        │
│              ↓                                               │
│       DecisionEngine → Recommendations + RiskAlerts          │
│              ↓                                               │
│       ActionExecutor ← ConfirmDialog (semi-bot)              │
│              ↓                                               │
│       PauseController (F1 automatico)                        │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│              Config + Persistence Layer                      │
│  AppConfig  |  BotParams  |  Telemetry  |  RulesIndex        │
│  ~/.eu4-assistant/config.json + bot_params.json              │
└──────────────────────────────────────────────────────────────┘
                            ↕
┌──────────────────────────────────────────────────────────────┐
│                  EU4 File System                             │
│  autosave.eu4  |  dlc_load.json  |  mod/*.mod  |  common/   │
└──────────────────────────────────────────────────────────────┘
```

---

## 8. Moduli

### 8.1 `eu4_assistant_bot.watcher` *(M4)*
- `watchdog` monitora `autosave.eu4`, emette `SaveChanged` con debounce 500ms.
- Thread separato, comunica via queue thread-safe.
- Emette anche `GamePaused` se nessun nuovo autosave arriva entro un timeout configurabile (default: 3 minuti) — segnala al bot di entrare in pausa automatica.

### 8.2 `eu4_assistant_bot.parser` *(M3)*
- `ClausewitzTextParser`: parser ricorsivo completo per save testuali.
  - Gestisce blocchi annidati, liste, stringhe quotate, date `YYYY.MM.DD`.
  - Output: albero dizionario Python nativo.
- `SaveUnzipper`: decompressione ZIP pre-parsing.

### 8.3 `eu4_assistant_bot.extractor` *(M4)*
- `StateExtractor`: albero Clausewitz grezzo → `GameSnapshot` tipizzato.
- Parsing difensivo su ogni campo, default safe se assente.
- Gestisce sezioni opzionali DLC (estates, parliaments, fervor, ecc.).

### 8.4 `eu4_assistant_bot.models` *(esteso M4, M6, M7)*
```python
@dataclass
class GameSnapshot:
    # Base
    timestamp: str
    eu4_date: str           # "1444.11.11"
    country: str
    stability: int          # -3 → +3
    prestige: float
    legitimacy: float
    # Esistenti
    economy: EconomyState
    military: MilitaryState
    diplomacy: DiplomacyState
    colonial: ColonialState
    risk: RiskState
    # M4
    tech: TechState         # adm/dip/mil + costo prossimo tech
    ideas: IdeasState       # gruppi completati, in corso, punti liberi
    # M6
    armies: list[ArmyState]            # posizione, composizione
    provinces: list[ProvinceState]     # unrest, owner, development
    # M7
    trade_nodes: list[TradeNodeState]  # power, value, merchants
```

### 8.4b Scope military bot in guerra

Durante una guerra attiva il military bot gestisce:
- **Movimento** — sposta eserciti verso il fronte / obiettivo
- **Assedi** — manda stack adeguato sulle province obiettivo
- **Ritirata** — evita battaglie sfavorevoli (strength check pre-ingaggio)
- **Ingaggio** — attacca quando il rapporto di forze è favorevole

**Trattative di pace:** sempre escluse dall'automazione. Il bot si ferma, notifica l'utente e aspetta conferma prima di procedere. Rientra nelle "azioni critiche" con possibilità di annulla.

**Comportamento con EU4 in pausa:** il bot rileva lo stato di pausa (nessun aggiornamento autosave) e rimane in attesa senza tentare azioni. Riprende automaticamente al prossimo autosave ricevuto.

**Activity feed:** ogni azione eseguita dal bot appare in tempo reale nel pannello Advisor (banner compatto sopra le recommendation cards) con: tipo azione, target, stato (in corso / completata / fallita).

### 8.5 `eu4_assistant_bot.decision_engine` *(esteso M6, M7)*
- Risk evaluation + top-3 raccomandazioni ordinate per priorità.
- **M6 — Military:** 
  - *Peacetime:* stack scoring vs combat width, alert eserciti sotto-dimensionati, reclutamento
  - *Wartime:* routing eserciti verso fronte/assedi, valutazione battle odds (ingaggio se favorevole, ritirata se sfavorevole)
  - *Pace gate:* trattative di pace sempre in coda conferma, mai eseguite in autonomia
- **M7 — Colonial:** due modalità operative:
  - *Autonomo*: ranking province per valore × sicurezza, sceglie e colonizza in autonomia.
  - *Lista target*: il giocatore spunta province specifiche, il bot le colonizza in ordine.
  La modalità attiva è configurabile dal pannello full-bot e persistente tra sessioni.
- **M7 — Economy:** steering mercanti, alert tech con MP insufficienti.
- Ogni raccomandazione include: titolo, categoria, score, testo "perché", flag `executable: bool`.

### 8.6 `eu4_assistant_bot.executor` *(M8)*
- `ActionExecutor` reale via `pyautogui` + `win32api`.
- Ogni `ActionHandler`: `pre_check() → execute() → post_check()`.
- `ConfirmationDialog` (semi-bot): mostra dettaglio azione, attende conferma.
- `ExecutionSupervisor`: retry, fallback, stop emergenza.
- Azioni v1.0:
  - *Peacetime:* reclutamento truppe, invio colono, miglioramento relazioni, riduzione manutenzione
  - *Wartime:* movimento eserciti verso fronte, assedio obiettivi, ritirata da battaglie sfavorevoli, ingaggio battaglie favorevoli
  - *Mai automatiche (richiedono sempre conferma):* trattative di pace, cessione province, pagamento indennità
- **Live action display:** ogni azione in esecuzione mostra un banner "Sto eseguendo: [azione]" in cima all'Advisor, sostituisce le recommendation cards durante l'esecuzione.
- **Annulla ultima azione:** disponibile solo per azioni critiche (pace, cessione province, indennità elevate) tramite tasto dedicato nel banner di conferma. Non implementato per azioni reversibili.
- **Comportamento se EU4 è in pausa:** il bot rileva che il gioco è fermo (nessun nuovo autosave dopo timeout configurabile), entra in stato `pausa automatica` e mostra avviso "EU4 in pausa — bot in attesa". Riprende automaticamente al primo nuovo autosave.

### 8.7 `eu4_assistant_bot.pause_controller` *(M5)*
- Monitora snapshot per condizioni di pausa automatica.
- Invia keypress `F1` a EU4 quando rileva:
  - Unrest massimo in almeno una provincia (`rebels_imminent`)
  - Nuovo stato di guerra attivo dichiarato contro il giocatore (`war_declared`)
- Log dell'evento nel feed UI.

### 8.8 `eu4_assistant_bot.ui` *(M5)*
Costruito con PyQt6. Layout a tre colonne sul secondo monitor.

**Dashboard (sinistra):**
- Bandiera + tag + data in-game
- Barre: treasury / income / expenses / debt
- Manpower, force limit, stability, prestige, legitimacy

**Advisor (centro — principale):**
- Top-3 recommendation cards sempre visibili (anche senza alert attivi): titolo, categoria, score, testo "perché"
- Pulsante **[Esegui]** su ogni card eseguibile
- Badge alert visivi (AE, coalition, debt, manpower, rebels, war)
- Switch modalità: `Advisor | ⏸ Full-bot` con stato bot visibile (attivo / pausa / errore / off)
- Pannello parametri full-bot (espandibile): budget, limiti, categorie abilitate, modalità colonial (autonomo / lista target)
- Soglie alert configurabili: coalition risk threshold, manpower ratio threshold (le altre usano default)

**Log (destra):**
- Feed eventi cronologico in tempo reale
- Filtro: decision / action / alert / error
- Export CSV a fine sessione

**Comportamento finestra:**
- Posizione e dimensioni persistenti tra sessioni
- Hotkey `F2` mostra/nasconde
- Tema scuro nativo

### 8.9 `eu4_assistant_bot.mod` *(M3)*
Mod minimale che forza autosave mensile:
```
eu4_assistant_autosave/
├── eu4_assistant_autosave.mod       # name + supported_version
└── events/
    └── monthly_save.txt             # on_monthly_pulse → save_game = yes
```
Non altera regole di gioco. Compatibile con achievement.

### 8.10 `eu4_assistant_bot.config` *(esteso M4)*
- Rilevamento automatico percorsi EU4 e Documents al primo avvio.
- Persistenza su `~/.eu4-assistant/`:
  - `config.json` — percorsi, preferenze UI, modalità attiva, hotkey
  - `bot_params.json` — parametri full-bot (budget, limiti, categorie abilitate)
  - `changelog_seen.txt` — versione ultimo changelog visualizzato

### 8.11 `eu4_assistant_bot.telemetry` *(esteso M5)*
- Structured logging su `events.jsonl` (rotante).
- Changelog versione mostrato al primo avvio post-aggiornamento.
- Report sessione esportabile (JSON + testo leggibile).

---

## 9. Snapshot completo v1.0

```json
{
  "timestamp": "2026-03-11T10:00:00+00:00",
  "eu4_date": "1460.06.01",
  "country": "POR",
  "stability": 1,
  "prestige": 45.2,
  "legitimacy": 82.0,
  "economy": {
    "treasury": 120.5, "income": 18.3,
    "expenses": 14.1, "debt": 0, "merchants_deployed": 3
  },
  "tech": { "adm": 4, "dip": 4, "mil": 4,
            "adm_cost": 100, "dip_cost": 100, "mil_cost": 100 },
  "ideas": {
    "completed_groups": ["exploration"],
    "in_progress": "expansion", "free_ideas": 2
  },
  "military": {
    "force_limit": 28, "manpower": 22000,
    "armies": [
      { "id": "army_1", "location": "Lisboa", "troops": 18000,
        "composition": {"infantry": 12, "cavalry": 3, "artillery": 3} }
    ]
  },
  "diplomacy": {
    "truces": [{"tag": "CAS", "expires": "1462.03.01"}],
    "alliances": ["ENG"],
    "ae_map": {"CAS": 12, "FRA": 5}
  },
  "colonial": {
    "colonists_free": 1,
    "active_colonies": [{"province": "Azores", "progress": 400}]
  },
  "trade_nodes": [
    {"id": "Sevilla", "our_power": 35.2, "total_value": 12.8, "merchants": 1}
  ],
  "risk": { "coalition": 0.12, "rebels": 0.05, "ae_max": 12 },
  "alerts": {
    "rebels_imminent": false,
    "war_declared": false
  }
}
```

---

## 10. Pipeline live update

```
[EU4 scrive autosave.eu4]
        ↓
[FileWatcher rileva modifica → debounce 500ms]
        ↓
[SaveUnzipper → estrae da ZIP]
        ↓
[ClausewitzTextParser → albero raw]
        ↓
[StateExtractor → GameSnapshot tipizzato]
        ↓
[PauseController → pausa EU4 se necessario (F1)]
        ↓
[DecisionEngine → RiskAlerts + top-3 Recommendations]
        ↓
[UI.update_signal → Dashboard + Advisor + Log aggiornati]
        ↓  (solo se full-bot attivo)
[ActionExecutor → esecuzione autonoma entro guardrail]
```

**Latenza attesa:** 1–3 secondi dal file scritto all'UI aggiornata.

---

## 11. Roadmap milestone v1.0

| Milestone | Contenuto | Dipendenze |
|---|---|---|
| **M1** ✅ | Foundation: config, models, telemetry, parser PoC, CLI | — |
| **M2** ✅ | Decision engine + risk alerts + simulated executor | M1 |
| **M3** | ClausewitzTextParser completo + SaveUnzipper + mod autosave | M1 |
| **M4** | FileWatcher + StateExtractor + GameSnapshot v2 + DLC compat + path autodetect | M3 |
| **M5** | UI PyQt6 base (Dashboard + Advisor + Log, dati live) + PauseController + hotkey | M4 |
| **M6** | Military logic reale (stack scoring, army advisor) | M4, M5 |
| **M7** | Colonial + Economy logic reale | M4, M5 |
| **M8** | ActionExecutor reale (pyautogui) + semi-bot confirm + full-bot params UI | M5, M6, M7 |
| **M9** | QA: test end-to-end, stabilità, crash hardening, DLC regression | tutti |
| **M10** | Packaging PyInstaller + changelog system + docs | M9 |
| **v1.0** | Release stabile | M10 |

---

## 12. Rischi tecnici e mitigazioni

| Rischio | Probabilità | Mitigazione |
|---|---|---|
| Patch EU4 cambia struttura save | Alta | Layer adapter versionato, test su sample save aggiornati |
| Sezione DLC assente in save vecchi/nuovi | Alta | Parsing difensivo con default safe su ogni campo |
| pyautogui perde posizione UI dopo patch | Alta | Template matching con confidence threshold, fallback + log |
| Parsing lento su save grandi (>30MB) | Media | Lazy extraction per sezioni, profiling su campagne avanzate |
| Mod QoL altera struttura save marginalmente | Bassa | Test con mod popolari (BetterUI, SMAN, ecc.) |
| Falsa pausa automatica (false positive) | Media | Soglie conservative configurabili, log motivazione pausa |

---

## 13. Definizione di "Done" per v1.0

- [ ] Mod autosave mensile funzionante e documentata
- [ ] Save file parsato correttamente (campagna normale, tutti i DLC)
- [ ] File watcher live stabile per tutta la durata di una campagna
- [ ] Rilevamento automatico percorsi EU4 al primo avvio
- [ ] UI sul secondo monitor con dati live, tema scuro, in italiano
- [ ] Top-3 raccomandazioni con spiegazione leggibile
- [ ] Pulsante [Esegui] funzionante su ogni raccomandazione eseguibile
- [ ] Alert attivi: AE, coalition, debt, manpower, rebels, war
- [ ] Pausa automatica EU4 su ribellione imminente e guerra dichiarata
- [ ] Hotkey F2 mostra/nasconde finestra
- [ ] Military advisor: stack scoring + alert eserciti
- [ ] Colonial advisor: ranking province + gestione coloni
- [ ] Economy advisor: steering mercanti, alert tech
- [ ] Full-bot con parametri configurabili e persistenti
- [ ] Switch full-bot disattivabile istantaneamente
- [ ] Log sessione esportabile in CSV
- [ ] Changelog mostrato a ogni aggiornamento
- [ ] Military bot wartime: movimento, assedi, ingaggio e ritirata funzionanti
- [ ] Pace gate: trattative di pace sempre in coda conferma
- [ ] Live action display: banner azione in corso sull'Advisor
- [ ] Annulla azione: disponibile su azioni critiche
- [ ] Bot entra in pausa automatica se EU4 è fermo
- [ ] Colonial bot: modalità autonoma e lista target entrambe funzionanti
- [ ] Full-bot: stati attivo / pausa / errore / off distinti e visibili
- [ ] Gestione errori bot: notifica visiva + suono, distinzione critico/minore
- [ ] Soglie alert configurabili: coalition e manpower threshold
- [ ] Template matching basato su UI inglese (immune alla mod traduzione IT)
- [ ] Military bot: movimento, assedi, ritirata e ingaggio durante guerra
- [ ] Trattative di pace sempre con conferma utente (azione critica)
- [ ] Bot in attesa se EU4 è in pausa, resume automatico al prossimo save
- [ ] Activity feed azioni bot in tempo reale nel pannello Advisor
- [ ] Nessun crash su campagna completa (1444 → fine partita)
- [ ] Eseguibile Windows standalone senza dipendenze esterne

---

## 14. Stato progetto

| Milestone | Stato |
|---|---|
| M1 — Foundation | ✅ Completato |
| M2 — Decision engine + simulated executor | ✅ Completato |
| M3 — Parser Clausewitz completo + mod | ⏳ Prossimo |
| M4 — FileWatcher + StateExtractor + DLC compat | 🔜 Pianificato |
| M5 — UI PyQt6 + PauseController + hotkey | 🔜 Pianificato |
| M6 — Military logic | 🔜 Pianificato |
| M7 — Colonial + Economy logic | 🔜 Pianificato |
| M8 — ActionExecutor reale + full-bot UI | 🔜 Pianificato |
| M9 — QA / stabilità / crash hardening | 🔜 Pianificato |
| M10 — Packaging + changelog | 🔜 Pianificato |
