from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .models import GameSnapshot

logger = logging.getLogger(__name__)


class PauseTrigger(str, Enum):
    REBELS_IMMINENT = "rebels_imminent"   # unrest critico in almeno una provincia
    WAR_DECLARED    = "war_declared"      # nuovo stato di guerra contro il giocatore


@dataclass
class PauseEvent:
    trigger: PauseTrigger
    detail: str = ""


# Soglia unrest sopra cui consideriamo la ribellione imminente
_REBELS_RISK_THRESHOLD = 0.6


class PauseController:
    """Monitora lo snapshot e invia F1 a EU4 quando serve la pausa automatica.

    Il controller confronta lo snapshot corrente con quello precedente per
    rilevare transizioni (es. nuova guerra dichiarata). Non invia F1 in modo
    ripetuto per la stessa condizione: una pausa per trigger viene emessa una
    sola volta finché la condizione non si azzera e ripresenta.

    Args:
        send_pause_fn: Callable che esegue il keypress F1 su EU4.
            Di default usa ``keyboard.press('f1')``.
            Può essere sostituito nei test con un mock.
        on_pause: Callback opzionale chiamato con ``PauseEvent`` dopo ogni pausa.
    """

    def __init__(
        self,
        send_pause_fn: Callable[[], None] | None = None,
        on_pause: Callable[[PauseEvent], None] | None = None,
    ) -> None:
        self._send_pause = send_pause_fn or self._default_send_pause
        self._on_pause   = on_pause
        self._prev_snapshot: GameSnapshot | None = None
        self._active_triggers: set[PauseTrigger] = set()

    def update(self, snapshot: GameSnapshot) -> list[PauseEvent]:
        """Valuta il nuovo snapshot ed emette pause se necessario.

        Returns:
            Lista di PauseEvent emessi in questa chiamata (vuota se nessuna pausa).
        """
        events: list[PauseEvent] = []

        # ── Ribellione imminente ──────────────────────────────────────────────
        rebels_critical = snapshot.risk.rebels >= _REBELS_RISK_THRESHOLD
        if rebels_critical and PauseTrigger.REBELS_IMMINENT not in self._active_triggers:
            event = PauseEvent(
                trigger=PauseTrigger.REBELS_IMMINENT,
                detail=f"Rischio ribellione critico: {snapshot.risk.rebels:.0%}",
            )
            self._emit(event)
            events.append(event)
            self._active_triggers.add(PauseTrigger.REBELS_IMMINENT)
        elif not rebels_critical:
            self._active_triggers.discard(PauseTrigger.REBELS_IMMINENT)

        # ── Nuova guerra dichiarata ───────────────────────────────────────────
        if self._prev_snapshot is not None:
            prev_truces = {t.get("who", "") for t in self._prev_snapshot.diplomacy.truces}
            curr_truces = {t.get("who", "") for t in snapshot.diplomacy.truces}
            new_enemies = curr_truces - prev_truces  # nazioni entrate in guerra

            # Proxy: se appaiono nuove truces NON presenti prima → guerra terminata/dichiarata
            # Alternativa più robusta in M6: campo is_at_war su snapshot
            if new_enemies and PauseTrigger.WAR_DECLARED not in self._active_triggers:
                event = PauseEvent(
                    trigger=PauseTrigger.WAR_DECLARED,
                    detail=f"Nuova guerra rilevata contro: {', '.join(new_enemies)}",
                )
                self._emit(event)
                events.append(event)
                self._active_triggers.add(PauseTrigger.WAR_DECLARED)
        elif not snapshot.diplomacy.truces:
            self._active_triggers.discard(PauseTrigger.WAR_DECLARED)

        self._prev_snapshot = snapshot
        return events

    def reset(self) -> None:
        """Azzera lo stato interno (es. a inizio sessione)."""
        self._prev_snapshot = None
        self._active_triggers.clear()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _emit(self, event: PauseEvent) -> None:
        logger.info("PauseController: %s — %s", event.trigger.value, event.detail)
        try:
            self._send_pause()
        except Exception as exc:  # pragma: no cover
            logger.error("PauseController: impossibile inviare F1: %s", exc)
        if self._on_pause:
            self._on_pause(event)

    @staticmethod
    def _default_send_pause() -> None:
        import keyboard  # import lazy — non disponibile in headless CI
        keyboard.press("f1")
