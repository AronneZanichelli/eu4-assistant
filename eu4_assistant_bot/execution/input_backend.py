"""Abstract input backend for OS-level GUI interaction."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class InputBackend(ABC):
    """Abstract interface for OS-level input injection.

    Implementations:
    - PyAutoGuiBackend: real clicks/keys via pyautogui (Windows, requires pyautogui)
    - StubBackend: records calls for testing, no real input
    """

    @abstractmethod
    def click(self, x: int, y: int) -> None:
        """Left-click at screen coordinates."""

    @abstractmethod
    def right_click(self, x: int, y: int) -> None:
        """Right-click at screen coordinates."""

    @abstractmethod
    def send_key(self, key: str) -> None:
        """Press a single key (e.g. 'f1', 'escape', 'enter')."""

    @abstractmethod
    def type_text(self, text: str) -> None:
        """Type a string character by character."""

    @abstractmethod
    def screenshot_region(self, x: int, y: int, w: int, h: int) -> bytes:
        """Return PNG bytes of the specified screen region."""

    @abstractmethod
    def locate_template(
        self, template_name: str, region: tuple[int, int, int, int] | None = None
    ) -> tuple[int, int] | None:
        """Find a template image on screen, return center coords or None."""

    @abstractmethod
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> None:
        """Drag from start to end coordinates."""


class PyAutoGuiBackend(InputBackend):
    """Real implementation using pyautogui for GUI automation."""

    def __init__(self) -> None:
        try:
            import pyautogui  # noqa: F401

            self._pyautogui = pyautogui
            self._pyautogui.FAILSAFE = True
            self._pyautogui.PAUSE = 0.1
        except ImportError:
            raise RuntimeError(
                "pyautogui not installed. Install with: pip install eu4-assistant-bot[bot]"
            )

    def click(self, x: int, y: int) -> None:
        self._pyautogui.click(x, y)

    def right_click(self, x: int, y: int) -> None:
        self._pyautogui.rightClick(x, y)

    def send_key(self, key: str) -> None:
        self._pyautogui.press(key)

    def type_text(self, text: str) -> None:
        self._pyautogui.typewrite(text, interval=0.02)

    def screenshot_region(self, x: int, y: int, w: int, h: int) -> bytes:
        import io

        img = self._pyautogui.screenshot(region=(x, y, w, h))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def locate_template(
        self, template_name: str, region: tuple[int, int, int, int] | None = None
    ) -> tuple[int, int] | None:
        try:
            location = self._pyautogui.locateOnScreen(template_name, region=region, confidence=0.8)
            if location is not None:
                center = self._pyautogui.center(location)
                return (int(center.x), int(center.y))
        except Exception:
            logger.debug("Template '%s' not found on screen", template_name)
        return None

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> None:
        self._pyautogui.moveTo(start_x, start_y)
        self._pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)


class StubBackend(InputBackend):
    """Test backend that records all calls without performing real input."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.template_results: dict[str, tuple[int, int] | None] = {}

    def click(self, x: int, y: int) -> None:
        self.calls.append(("click", (x, y)))

    def right_click(self, x: int, y: int) -> None:
        self.calls.append(("right_click", (x, y)))

    def send_key(self, key: str) -> None:
        self.calls.append(("send_key", (key,)))

    def type_text(self, text: str) -> None:
        self.calls.append(("type_text", (text,)))

    def screenshot_region(self, x: int, y: int, w: int, h: int) -> bytes:
        self.calls.append(("screenshot_region", (x, y, w, h)))
        return b""

    def locate_template(
        self, template_name: str, region: tuple[int, int, int, int] | None = None
    ) -> tuple[int, int] | None:
        self.calls.append(("locate_template", (template_name, region)))
        return self.template_results.get(template_name)

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> None:
        self.calls.append(("drag", (start_x, start_y, end_x, end_y)))
