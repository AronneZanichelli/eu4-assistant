"""F2 global hotkey for show/hide window toggle (M5).

Uses pynput for cross-platform global hotkey listening.
"""
from __future__ import annotations

import logging
from typing import Callable

from pynput.keyboard import Key, Listener

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Listens for F2 (configurable) and invokes a callback.

    Parameters
    ----------
    callback : callable
        Called (in the listener thread) when the hotkey is pressed.
    key : Key
        The key to listen for. Defaults to F2.
    """

    def __init__(
        self,
        callback: Callable[[], None],
        key: Key = Key.f2,
    ) -> None:
        self._callback = callback
        self._key = key
        self._listener: Listener | None = None

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()
        logger.info("HotkeyManager: listening for %s", self._key)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            logger.info("HotkeyManager: stopped")

    def _on_press(self, key: Key | None) -> None:
        if key == self._key:
            try:
                self._callback()
            except Exception:  # noqa: BLE001
                logger.exception("HotkeyManager: callback error")
