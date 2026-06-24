"""Tests for HotkeyManager — lazy pynput import (M3)."""
from __future__ import annotations

from eu4_assistant_bot.ui.hotkey import HotkeyManager


def test_construction_does_not_require_pynput() -> None:
    """Constructing must not import the pynput backend (M3 lazy import).

    This environment has no pynput installed; if importing the module or
    constructing the manager pulled pynput, this would raise ImportError.
    """
    calls: list[int] = []
    hk = HotkeyManager(callback=lambda: calls.append(1), key="f2")
    assert hk._key_name == "f2"
    assert hk._listener is None


def test_stop_before_start_is_noop() -> None:
    """stop() on a never-started manager must be a safe no-op."""
    hk = HotkeyManager(callback=lambda: None)
    hk.stop()
    assert hk._listener is None
