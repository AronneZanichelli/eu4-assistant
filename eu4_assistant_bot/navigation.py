"""Screen navigation primitives for real in-game action execution (AUTO-01).

:class:`Navigator` wraps screen capture (pyautogui / Pillow), template
matching (cv2 + numpy) and mouse clicks (pyautogui) behind a clean object
boundary so executors can be tested headless, without any optional backends.

All backends are lazy-imported and fail soft — Navigator degrades to no-op
when ``cv2`` or ``pyautogui`` are absent.  Install
``eu4-assistant-bot[bot]`` to enable real navigation.

Template assets live in ``eu4_assistant_bot/templates/`` and **must** be
captured from the **English base UI** (not the Italian translation mod) at
the resolution documented alongside each asset — design §6.5.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Directory that holds the PNG template assets shipped with the package.
_TEMPLATE_DIR: Path = Path(__file__).parent / "templates"

# Default confidence threshold for cv2.matchTemplate (TM_CCOEFF_NORMED).
DEFAULT_THRESHOLD: float = 0.8


@dataclass(slots=True)
class TemplateMatch:
    """Screen-coordinate centre of a cv2 template match plus its confidence score."""

    x: int   # pixel column of the match centre
    y: int   # pixel row of the match centre
    confidence: float


class Navigator:
    """Screen-navigation primitives: capture → template-match → click.

    Designed for dependency injection: construct with default (real) callables
    in production; inject a :class:`tests.test_navigation._FakeNavigator`-style
    recorder in tests (codebase favours DI over mocking).

    All public methods return falsy / empty on failure — they never raise.
    """

    def capture(self, region: tuple[int, int, int, int] | None = None) -> Any | None:
        """Take a screenshot and return a Pillow Image, or None on failure.

        Args:
            region: ``(left, top, width, height)`` in screen pixels, or None
                for the full primary monitor.
        """
        try:
            import pyautogui  # type: ignore[import]  # noqa: PLC0415
        except ImportError:
            logger.warning(
                "pyautogui not installed — install eu4-assistant-bot[bot] for "
                "screen capture support.  Navigation disabled."
            )
            return None
        try:
            img = pyautogui.screenshot(region=region)
            logger.debug("Screenshot captured (region=%s).", region)
            return img
        except Exception as exc:  # noqa: BLE001
            logger.warning("Screenshot failed: %s", exc)
            return None

    def find(
        self,
        template_name: str,
        image: Any,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> list[TemplateMatch]:
        """Locate all instances of *template_name* in *image* above *threshold*.

        Template PNGs are loaded from ``eu4_assistant_bot/templates/``.  The
        English base-UI constraint (design §6.5) is enforced by the asset
        directory — no Italian-UI templates are ever committed there.

        Args:
            template_name: File stem of the PNG template (e.g.
                ``"colonize_button"``).
            image: Pillow Image as returned by :meth:`capture`.
            threshold: Match confidence in [0, 1]; defaults to
                :data:`DEFAULT_THRESHOLD`.

        Returns:
            Matches sorted by confidence descending, empty list on any failure.
        """
        if image is None:
            return []
        template_path = _TEMPLATE_DIR / f"{template_name}.png"
        if not template_path.exists():
            logger.warning("Template not found: %s", template_path)
            return []
        try:
            import cv2  # type: ignore[import]  # noqa: PLC0415
            import numpy as np  # type: ignore[import]  # noqa: PLC0415
        except ImportError:
            logger.warning(
                "cv2/numpy not installed — install eu4-assistant-bot[bot] for "
                "template matching support.  Navigation disabled."
            )
            return []
        try:
            # Pillow Image → BGR numpy array for cv2.  ascontiguousarray is
            # required: the [::-1] channel flip yields negative strides, which
            # cv2.matchTemplate rejects as non-C-contiguous input.
            img_np = np.ascontiguousarray(np.array(image.convert("RGB"))[:, :, ::-1])
            tpl_np = cv2.imread(str(template_path))
            if tpl_np is None:
                logger.warning("cv2 could not read template: %s", template_path)
                return []
            result = cv2.matchTemplate(img_np, tpl_np, cv2.TM_CCOEFF_NORMED)
            tpl_h, tpl_w = tpl_np.shape[:2]
            locations = np.where(result >= threshold)
            matches: list[TemplateMatch] = []
            for pt_y, pt_x in zip(locations[0], locations[1], strict=False):
                conf = float(result[pt_y, pt_x])
                cx = int(pt_x) + tpl_w // 2
                cy = int(pt_y) + tpl_h // 2
                matches.append(TemplateMatch(x=cx, y=cy, confidence=conf))
            matches.sort(key=lambda m: m.confidence, reverse=True)
            logger.debug(
                "Template '%s': %d match(es) above %.2f.",
                template_name,
                len(matches),
                threshold,
            )
            return matches
        except Exception as exc:  # noqa: BLE001
            logger.warning("Template matching failed for '%s': %s", template_name, exc)
            return []

    def click(self, x: int, y: int) -> bool:
        """Move the mouse to *(x, y)* and left-click.  Returns True if sent.

        ``pyautogui.FAILSAFE`` is enforced before every click — dragging the
        mouse to a screen corner aborts the bot immediately (design §6.5).
        """
        try:
            import pyautogui  # type: ignore[import]  # noqa: PLC0415
        except ImportError:
            logger.warning(
                "pyautogui not installed — install eu4-assistant-bot[bot] for "
                "mouse click support.  Navigation disabled."
            )
            return False
        pyautogui.FAILSAFE = True
        try:
            pyautogui.click(x, y)
            logger.debug("Clicked (%d, %d).", x, y)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Click at (%d, %d) failed: %s", x, y, exc)
            return False


def nearest_to_center(
    matches: list[TemplateMatch],
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> TemplateMatch | None:
    """Return the match closest to the screen centre (Euclidean distance).

    Tie-breaking is deterministic: smallest x wins, then smallest y.
    Returns None when *matches* is empty.

    This implements the AUTO-01 targeting strategy: "click nearest colonizable
    in view" (design §6.5).  Province ranking from
    :meth:`~eu4_assistant_bot.decision_engine.DecisionEngine.rank_colonizable`
    is preserved as advisory; the bot always targets the visually nearest marker.
    """
    if not matches:
        return None
    cx = screen_width / 2.0
    cy = screen_height / 2.0

    def _key(m: TemplateMatch) -> tuple[float, int, int]:
        dist = math.sqrt((m.x - cx) ** 2 + (m.y - cy) ** 2)
        return (dist, m.x, m.y)

    return min(matches, key=_key)
