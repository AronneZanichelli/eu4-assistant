from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


# ── Events ────────────────────────────────────────────────────────────────────

class SaveEventType(str, Enum):
    SAVE_CHANGED = "save_changed"
    GAME_PAUSED  = "game_paused"   # no new save within pause_timeout seconds


@dataclass
class SaveEvent:
    type: SaveEventType
    path: Path | None = None       # set for SAVE_CHANGED


# ── Internal watchdog handler ─────────────────────────────────────────────────

class _SaveFileHandler(FileSystemEventHandler):
    def __init__(
        self,
        target: Path,
        callback: Callable[[Path], None],
        debounce: float,
    ) -> None:
        super().__init__()
        self._target   = target
        self._callback = callback
        self._debounce = debounce
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if Path(event.src_path).resolve() != self._target.resolve():
            return
        self._schedule()

    def on_created(self, event: FileSystemEvent) -> None:
        self.on_modified(event)

    def _schedule(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def _fire(self) -> None:
        with self._lock:
            self._timer = None
        self._callback(self._target)


# ── Public FileWatcher ────────────────────────────────────────────────────────

class FileWatcher:
    """Watches an EU4 autosave file and emits SaveEvents on a thread-safe queue.

    Events:
        SAVE_CHANGED — emitted (after debounce) when the file is written.
        GAME_PAUSED  — emitted when no new save arrives within pause_timeout seconds.

    Usage::

        watcher = FileWatcher(Path("...autosave.eu4"))
        watcher.start()
        while True:
            event = watcher.get(timeout=5)
            if event:
                process(event)
        watcher.stop()
    """

    def __init__(
        self,
        save_path: Path,
        debounce: float = 0.5,
        pause_timeout: float = 180.0,
        _poll_interval: float = 10.0,
    ) -> None:
        self._save_path     = save_path.resolve()
        self._debounce      = debounce
        self._pause_timeout = pause_timeout
        self._poll_interval = _poll_interval

        self._queue: queue.Queue[SaveEvent] = queue.Queue()
        self._observer: Observer | None = None
        self._pause_thread: threading.Thread | None = None
        self._last_change  = time.monotonic()
        self._running      = False

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start watching the file. Safe to call multiple times."""
        if self._running:
            return
        self._running = True
        self._last_change = time.monotonic()

        handler = _SaveFileHandler(
            self._save_path,
            callback=self._on_save_changed,
            debounce=self._debounce,
        )
        self._observer = Observer()
        self._observer.schedule(handler, str(self._save_path.parent), recursive=False)
        self._observer.start()

        self._pause_thread = threading.Thread(
            target=self._pause_monitor, daemon=True, name="eu4-pause-monitor"
        )
        self._pause_thread.start()
        logger.info("FileWatcher started: watching %s", self._save_path)

    def stop(self) -> None:
        """Stop the watcher. Blocks until background threads exit."""
        self._running = False
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
        logger.info("FileWatcher stopped.")

    def get(self, timeout: float | None = None) -> SaveEvent | None:
        """Return the next SaveEvent from the queue, or None on timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_save_changed(self, path: Path) -> None:
        self._last_change = time.monotonic()
        event = SaveEvent(type=SaveEventType.SAVE_CHANGED, path=path)
        self._queue.put(event)
        logger.debug("SaveEvent: SAVE_CHANGED — %s", path)

    def _pause_monitor(self) -> None:
        """Background thread: emits GAME_PAUSED if no save within pause_timeout."""
        while self._running:
            time.sleep(self._poll_interval)
            if not self._running:
                break
            elapsed = time.monotonic() - self._last_change
            if elapsed >= self._pause_timeout:
                self._queue.put(SaveEvent(type=SaveEventType.GAME_PAUSED))
                logger.debug("SaveEvent: GAME_PAUSED (no save for %.0fs)", elapsed)
                # reset so we don't spam the queue
                self._last_change = time.monotonic()
