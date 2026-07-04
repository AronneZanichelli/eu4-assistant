"""Tests for navigation.Navigator and nearest_to_center (AUTO-01).

Navigator's real backends (pyautogui / cv2) are absent in dev, so these tests
assert graceful degradation (capture→None, find→[], click→False).
``nearest_to_center`` is pure and fully covered headless.
"""

from eu4_assistant_bot.navigation import Navigator, TemplateMatch, nearest_to_center


# ── nearest_to_center (pure targeting logic) ──────────────────────────────────

def test_nearest_to_center_empty_returns_none() -> None:
    assert nearest_to_center([]) is None


def test_nearest_to_center_picks_closest() -> None:
    far = TemplateMatch(x=10, y=10, confidence=0.9)
    near = TemplateMatch(x=960, y=540, confidence=0.5)  # screen centre @1920x1080
    # Targeting is by screen distance, not confidence: the low-confidence near
    # marker wins because "nearest in view" ignores the economic ranking.
    assert nearest_to_center([far, near]) is near


def test_nearest_to_center_deterministic_tiebreak() -> None:
    # Two markers equidistant from centre → smaller x wins (deterministic).
    left = TemplateMatch(x=860, y=540, confidence=0.5)
    right = TemplateMatch(x=1060, y=540, confidence=0.5)
    assert nearest_to_center([right, left]) is left


def test_nearest_to_center_respects_screen_size() -> None:
    a = TemplateMatch(x=100, y=100, confidence=0.5)
    b = TemplateMatch(x=300, y=300, confidence=0.5)
    # 400x400 screen → centre (200,200); both equidistant → tiebreak picks a.
    assert nearest_to_center([b, a], screen_width=400, screen_height=400) is a


# ── Navigator graceful degradation (no cv2 / pyautogui backend in dev) ─────────

def test_capture_returns_none_without_backend() -> None:
    assert Navigator().capture() is None


def test_find_returns_empty_for_none_image() -> None:
    assert Navigator().find("colonizable_marker", None) == []


def test_find_returns_empty_for_missing_template() -> None:
    # A truthy image clears the None guard; an unknown template stem yields [].
    assert Navigator().find("does_not_exist", object()) == []


def test_click_returns_false_without_backend() -> None:
    assert Navigator().click(10, 20) is False
