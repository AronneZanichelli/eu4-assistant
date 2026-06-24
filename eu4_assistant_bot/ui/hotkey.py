"""F2 global hotkey for show/hide window toggle (M5).

Uses pynput for cross-platform global hotkey listening. pynput is imported
lazily (inside ``start``) so importing this module — and the UI package that
wires it — does not require the optional ``pynput``/``evdev`` backend to be
installed.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from pynput.keyboard import Key, Listener

logger = logging.getLogger(__name__)


class HotkeyManager:
    """Listens for a global hotkey (default F2) and invokes a callback.

    Parameters
    ----------
    callback : callable
        Called (in the listener thread) when the hotkey is pressed.
    key : str
        Name of the ``pynput.keyboard.Key`` to listen for (e.g. ``"f2"``).
        Resolved lazily when the listener starts, so construction never needs
        the pynput backend.
    """

    def __init__(
        self,
        callback: Callable[[], None],
        key: str = "f2",
    ) -> None:
        self._callback = callback
        self._key_name = key
        self._key: Key | None = None
        self._listener: Listener | None = None

    def start(self) -> None:
        if self._listener is not None:
            return
        from pynput.keyboard import Key, Listener  # noqa: PLC0415

        self._key = getattr(Key, self._key_name)
        self._listener = Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()
        logger.info("HotkeyManager: listening for %s", self._key_name)

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
