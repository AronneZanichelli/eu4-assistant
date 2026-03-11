from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


def setup_logging(log_dir: Path, level: str = "INFO") -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "eu4-assistant.log"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        force=True,
    )
    return log_file


def emit_event(event_path: Path, event_name: str, payload: dict[str, Any]) -> None:
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": event_name, "payload": payload}) + "\n")
