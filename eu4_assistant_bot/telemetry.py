from __future__ import annotations

import json
import logging
import logging.handlers
from enum import Enum
from pathlib import Path
from typing import Any


def _json_default(obj: Any) -> Any:
    """JSON serializer for objects not natively serializable."""
    if isinstance(obj, Enum):
        return obj.value
    return str(obj)


def setup_logging(log_dir: Path, level: str = "INFO") -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "eu4-assistant.log"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            ),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return log_file


def emit_event(event_path: Path, event_name: str, payload: dict[str, Any]) -> None:
    event_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with event_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"event": event_name, "payload": payload}, default=_json_default) + "\n")
    except Exception as exc:  # pragma: no cover
        logging.getLogger(__name__).error("Failed to emit event '%s': %s", event_name, exc)
