import time
from pathlib import Path

import pytest

from eu4_assistant_bot.watcher import FileWatcher, SaveEventType


def test_watcher_detects_file_change(tmp_path: Path) -> None:
    save = tmp_path / "autosave.eu4"
    save.write_text("date = 1444.11.11\n")

    watcher = FileWatcher(save, debounce=0.05, pause_timeout=999)
    watcher.start()
    try:
        time.sleep(0.1)
        save.write_text("date = 1444.12.01\n")
        event = watcher.get(timeout=3.0)
        assert event is not None
        assert event.type == SaveEventType.SAVE_CHANGED
        assert event.path == save.resolve()
    finally:
        watcher.stop()


def test_watcher_debounces_rapid_writes(tmp_path: Path) -> None:
    save = tmp_path / "autosave.eu4"
    save.write_text("date = 1444.11.11\n")

    watcher = FileWatcher(save, debounce=0.2, pause_timeout=999)
    watcher.start()
    try:
        time.sleep(0.1)
        # Write 5 times rapidly — should produce only 1 event
        for i in range(5):
            save.write_text(f"date = 1444.11.1{i}\n")
            time.sleep(0.02)
        time.sleep(0.5)
        events = []
        while True:
            e = watcher.get(timeout=0.1)
            if e is None:
                break
            events.append(e)
        assert len(events) == 1
    finally:
        watcher.stop()


def test_watcher_emits_game_paused(tmp_path: Path) -> None:
    save = tmp_path / "autosave.eu4"
    save.write_text("date = 1444.11.11\n")

    watcher = FileWatcher(save, debounce=0.05, pause_timeout=0.1, _poll_interval=0.05)
    watcher.start()
    try:
        # Wait for pause detection (timeout=0.1s, check every 10s normally,
        # but pause_timeout is tiny so it fires almost immediately)
        event = watcher.get(timeout=5.0)
        assert event is not None
        assert event.type == SaveEventType.GAME_PAUSED
    finally:
        watcher.stop()


def test_watcher_ignores_unrelated_files(tmp_path: Path) -> None:
    save = tmp_path / "autosave.eu4"
    save.write_text("date = 1444.11.11\n")
    other = tmp_path / "other.txt"

    watcher = FileWatcher(save, debounce=0.05, pause_timeout=999)
    watcher.start()
    try:
        time.sleep(0.1)
        other.write_text("unrelated\n")
        event = watcher.get(timeout=0.5)
        assert event is None
    finally:
        watcher.stop()


def test_watcher_stop_is_idempotent(tmp_path: Path) -> None:
    save = tmp_path / "autosave.eu4"
    save.write_text("")
    watcher = FileWatcher(save, debounce=0.05, pause_timeout=999)
    watcher.start()
    watcher.stop()
    watcher.stop()  # should not raise
