"""PauseController — automatic EU4 pause on critical events (M5).

Monitors GameSnapshot for two conditions:
  - rebels_imminent: unrest (risk.rebels) above threshold
  - war_declared:    new war detected (diplomacy changes)

When triggered, sends F1 keypress to EU4 to pause the game.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from .models import GameSnapshot

logger = logging.getLogger(__name__)


class PauseReason(str, Enum):
    REBELS_IMMINENT = "rebels_imminent"
    WAR_DECLARED = "war_declared"


@dataclass(slots=True)
class PauseEvent:
    """Emitted when the controller decides to pause the game."""
    reason: PauseReason
    message: str
    snapshot: GameSnapshot


class PauseController:
    """Monitors snapshots and pauses EU4 when critical conditions are detected.

    Parameters
    ----------
    rebels_threshold : float
        Risk.rebels value at or above which a pause is triggered.
    on_pause : callable, optional
        Callback invoked with a PauseEvent when a pause is triggered.
        If not provided, the event is only logged.
    send_key : callable, optional
        Callable that sends a keypress to the OS.  Defaults to an
        internal implementation that uses xdotool (Linux) or
        pyautogui-like fallback (Windows/macOS).  Override in tests.
    """

    def __init__(
        self,
        rebels_threshold: float = 0.60,
        on_pause: Callable[[PauseEvent], Any] | None = None,
        send_key: Callable[[str], None] | None = None,
    ) -> None:
        self._rebels_threshold = rebels_threshold
        self._on_pause = on_pause
        self._send_key = send_key or _default_send_key
        # Track previous snapshot to detect *new* wars
        self._prev_truces_count: int | None = None
        self._prev_alliances: set[str] | None = None
        # Cooldown: don't spam pause for the same reason within one cycle
        self._last_reason: PauseReason | None = None

    def check(self, snapshot: GameSnapshot) -> PauseEvent | None:
        """Evaluate snapshot and pause EU4 if critical condition detected.

        Returns the PauseEvent if a pause was triggered, else None.
        """
        event = self._evaluate(snapshot)
        if event is not None:
            self._send_key("F1")
            logger.info("PauseController: sent F1 — %s", event.message)
            if self._on_pause is not None:
                self._on_pause(event)
            self._last_reason = event.reason
        else:
            self._last_reason = None

        # Update state for next comparison
        self._prev_truces_count = len(snapshot.diplomacy.truces)
        self._prev_alliances = set(snapshot.diplomacy.alliances)
        return event

    def _evaluate(self, snap: GameSnapshot) -> PauseEvent | None:
        # 1. Rebels imminent
        if snap.risk.rebels >= self._rebels_threshold:
            if self._last_reason != PauseReason.REBELS_IMMINENT:
                return PauseEvent(
                    reason=PauseReason.REBELS_IMMINENT,
                    message=f"Unrest critico ({snap.risk.rebels:.2f} >= {self._rebels_threshold:.2f})",
                    snapshot=snap,
                )

        # 2. War declared — detect via new truces appearing
        #    (when someone declares war, a truce entry appears on next save)
        if self._prev_truces_count is not None:
            current_truces = len(snap.diplomacy.truces)
            if current_truces > self._prev_truces_count:
                if self._last_reason != PauseReason.WAR_DECLARED:
                    return PauseEvent(
                        reason=PauseReason.WAR_DECLARED,
                        message="Nuova guerra rilevata (truces aumentate)",
                        snapshot=snap,
                    )

        return None


def _default_send_key(key: str) -> None:
    """Send a keypress using platform-appropriate mechanism."""
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(
                ["xdotool", "key", key],
                check=True,
                timeout=3,
                capture_output=True,
            )
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            logger.warning("PauseController: xdotool failed: %s", exc)
    else:
        # Windows/macOS: use pynput as fallback
        try:
            from pynput.keyboard import Controller, Key
            kb = Controller()
            pynput_key = getattr(Key, key.lower(), None) or key
            kb.press(pynput_key)
            kb.release(pynput_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PauseController: pynput failed: %s", exc)
