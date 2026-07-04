"""Tests for ActionExecutor — simulate() (M1-M7) and execute() (M8 + M1 safety gate)."""

from eu4_assistant_bot.config import BotMode
from eu4_assistant_bot.executor import ActionExecutor
from eu4_assistant_bot.models import ActionPlan
from eu4_assistant_bot.navigation import TemplateMatch


# ── simulate() tests (unchanged) ──────────────────────────────────────────────

def test_simulate_skips_confirmation_in_assist_mode() -> None:
    plans = [
        ActionPlan(
            id="a:90",
            action_type="economy_stabilize_budget",
            priority=0.9,
            confidence=0.8,
            expected_outcome={"target_metric": "monthly_balance", "target_above": 0.0},
            requires_confirmation=True,
        )
    ]

    out = ActionExecutor().simulate(plans, mode=BotMode.ASSIST)

    assert len(out) == 1
    assert out[0].status == "skipped"
    assert out[0].reason == "confirmation_required_in_assist_mode"


def test_simulate_executes_in_semi_bot_mode() -> None:
    plans = [
        ActionPlan(
            id="m:80",
            action_type="military_recover_manpower",
            priority=0.8,
            confidence=0.75,
            expected_outcome={"target_metric": "manpower_ratio", "target_above": 0.2},
            requires_confirmation=True,
        )
    ]

    out = ActionExecutor().simulate(plans, mode=BotMode.SEMI_BOT)

    assert len(out) == 1
    assert out[0].status == "simulated_executed"
    assert out[0].simulated_effects["projected_direction"] == "up"


# ── execute() tests (M8 + M1 safety gate) ──────────────────────────────────────

def _make_plan(
    action_type: str = "economy_stabilize_budget",
    *,
    requires_confirmation: bool = True,
) -> ActionPlan:
    return ActionPlan(
        id="test:80",
        action_type=action_type,
        priority=0.8,
        confidence=0.75,
        expected_outcome={"target_metric": "monthly_balance", "target_above": 0.0},
        requires_confirmation=requires_confirmation,
    )


def _recorder():
    """Return (sent, sender): a key sender that records keys instead of touching pyautogui."""
    sent: list[str] = []

    def sender(key: str) -> bool:
        sent.append(key)
        return True

    return sent, sender


def test_execute_assist_mode_returns_advisory() -> None:
    """In ASSIST mode, execute() logs advice without game interaction."""
    out = ActionExecutor().execute([_make_plan()], mode=BotMode.ASSIST)

    assert len(out) == 1
    assert out[0].status == "advisory"
    assert out[0].reason == "assist_mode_advisory_only"


def test_execute_blocks_confirmation_required_without_confirm() -> None:
    """SEMI_BOT: a requires_confirmation plan is blocked when no confirm is given."""
    sent, sender = _recorder()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: True).execute(
        [_make_plan()], mode=BotMode.SEMI_BOT
    )

    assert out[0].status == "blocked"
    assert out[0].reason == "confirmation_required"
    assert sent == []  # no keystroke reached the game


def test_execute_full_bot_blocks_confirmation_required_without_confirm() -> None:
    """FULL_BOT cannot bypass the gate for a requires_confirmation plan."""
    sent, sender = _recorder()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: True).execute(
        [_make_plan(requires_confirmation=True)], mode=BotMode.FULL_BOT
    )

    assert out[0].status == "blocked"
    assert sent == []


def test_execute_semi_bot_with_confirm_sends_space() -> None:
    """SEMI_BOT with confirmation granted sends exactly the Space key."""
    sent, sender = _recorder()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: True).execute(
        [_make_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _plan: True
    )

    assert out[0].status == "executed"
    assert sent == ["space"]


def test_execute_full_bot_with_confirm_sends_space() -> None:
    """FULL_BOT with acknowledgement sends exactly the Space key."""
    sent, sender = _recorder()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: True).execute(
        [_make_plan()], mode=BotMode.FULL_BOT, confirm=lambda _plan: True
    )

    assert out[0].status == "executed"
    assert sent == ["space"]


def test_execute_full_bot_runs_autonomous_plan_without_confirm() -> None:
    """FULL_BOT runs a non-confirmation plan autonomously (SEMI/FULL distinction)."""
    sent, sender = _recorder()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: True).execute(
        [_make_plan(requires_confirmation=False)], mode=BotMode.FULL_BOT
    )

    assert out[0].status == "executed"
    assert sent == ["space"]


def test_execute_semi_bot_requires_confirm_even_for_autonomous_plan() -> None:
    """SEMI_BOT confirms every action, even one not flagged requires_confirmation."""
    sent, sender = _recorder()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: True).execute(
        [_make_plan(requires_confirmation=False)], mode=BotMode.SEMI_BOT
    )

    assert out[0].status == "blocked"
    assert sent == []


def test_execute_skips_keystroke_when_not_focused() -> None:
    """Even with confirmation, no key is sent when EU4 is not focused (focus guard)."""
    sent, sender = _recorder()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: False).execute(
        [_make_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _plan: True
    )

    assert out[0].status == "executed_no_pause"
    assert sent == []


def test_execute_returns_result_per_plan() -> None:
    plans = [_make_plan("economy_stabilize_budget"), _make_plan("military_recover_manpower")]

    out = ActionExecutor().execute(plans, mode=BotMode.ASSIST)

    assert len(out) == 2
    assert {r.action_type for r in out} == {"economy_stabilize_budget", "military_recover_manpower"}


def test_execute_simulated_effects_preserved() -> None:
    """execute() should include simulated_effects for UI compatibility."""
    out = ActionExecutor().execute([_make_plan()], mode=BotMode.ASSIST)

    assert "target_metric" in out[0].simulated_effects
    assert out[0].simulated_effects["projected_direction"] == "up"


def test_execute_confidence_preserved() -> None:
    plan = _make_plan()
    out = ActionExecutor().execute([plan], mode=BotMode.ASSIST)

    assert out[0].confidence == plan.confidence


def test_pause_game_returns_bool() -> None:
    """_pause_game() must always return a bool (True if sent, False on error/skip)."""
    result = ActionExecutor()._pause_game()

    assert isinstance(result, bool)


# ── colonize navigation (AUTO-01/02 first slice) ───────────────────────────────

_MARKER = TemplateMatch(x=100, y=100, confidence=0.9)
_BUTTON = TemplateMatch(x=200, y=200, confidence=0.95)


class _FakeImage:
    """Stand-in for a Pillow screenshot: exposes only ``.size`` like the real one."""

    def __init__(self, size: tuple[int, int] = (1920, 1080)) -> None:
        self.size = size


class _FakeNavigator:
    """Recorder navigator: scripts capture/find/click returns, records calls.

    Mirrors the DI-over-mocking pattern of ``_recorder`` above — no pyautogui/cv2
    is touched, so the colonize orchestration is tested fully headless.
    """

    def __init__(
        self,
        *,
        capture_returns: list | None = None,
        find_returns: dict[str, list[list[TemplateMatch]]] | None = None,
        click_returns: bool | list[bool] = True,
        image_size: tuple[int, int] = (1920, 1080),
    ) -> None:
        self._capture_returns = list(capture_returns) if capture_returns is not None else None
        self._find_returns = {k: list(v) for k, v in (find_returns or {}).items()}
        self._click_returns = click_returns
        self._image_size = image_size
        self.captures: list = []
        self.finds: list[str] = []
        self.clicks: list[tuple[int, int]] = []

    def capture(self, region=None):  # noqa: ANN001, ANN201
        self.captures.append(region)
        if self._capture_returns is None:
            return _FakeImage(self._image_size)
        return self._capture_returns.pop(0)

    def find(self, template_name: str, image, threshold: float = 0.8) -> list[TemplateMatch]:  # noqa: ANN001
        self.finds.append(template_name)
        queue = self._find_returns.get(template_name)
        if queue:
            return queue.pop(0)
        return []

    def click(self, x: int, y: int) -> bool:
        self.clicks.append((x, y))
        if isinstance(self._click_returns, list):
            return self._click_returns.pop(0)
        return self._click_returns


def _colonize_plan() -> ActionPlan:
    return ActionPlan(
        id="col:75",
        action_type="colonial_send_colonist",
        priority=0.75,
        confidence=0.7,
        expected_outcome={"target_metric": "colonists_free", "current_value": 1.0},
        requires_confirmation=True,
    )


def _colonize_executor(
    nav: _FakeNavigator, sleeps: list[float] | None = None
) -> ActionExecutor:
    """Executor with a recording no-op sleeper so tests never really sleep."""
    recorded = sleeps if sleeps is not None else []
    return ActionExecutor(
        focus_check=lambda: True, navigator=nav, sleeper=recorded.append
    )


def test_colonize_happy_path_clicks_marker_then_button() -> None:
    """colonial_send_colonist: marker → colonize button → consumed = colonize_started."""
    nav = _FakeNavigator(
        find_returns={
            "colonizable_marker": [[_MARKER]],
            "colonize_button": [[_BUTTON], []],  # present (pre-check), absent (post-check)
        }
    )
    out = _colonize_executor(nav).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "colonize_started"
    assert out[0].reason == "colonist_sent"
    assert nav.clicks == [(100, 100), (200, 200)]  # marker then button, in order


def test_colonize_no_marker_aborts_precheck() -> None:
    """No colonizable marker visible → precheck_failed, no clicks."""
    nav = _FakeNavigator(find_returns={"colonizable_marker": [[]]})
    out = _colonize_executor(nav).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "precheck_failed"
    assert out[0].reason == "no_colonizable_marker_visible"
    assert nav.clicks == []


def test_colonize_no_button_aborts_after_marker_click() -> None:
    """Marker clicked but no colonize button (false marker) → precheck_failed."""
    nav = _FakeNavigator(
        find_returns={"colonizable_marker": [[_MARKER]], "colonize_button": [[]]}
    )
    out = _colonize_executor(nav).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "precheck_failed"
    assert out[0].reason == "colonize_button_absent"
    assert nav.clicks == [(100, 100)]  # only the marker was clicked


def test_colonize_postcheck_mismatch_when_button_persists() -> None:
    """Button still present on every post-check attempt → postcheck_mismatch."""
    nav = _FakeNavigator(
        find_returns={
            "colonizable_marker": [[_MARKER]],
            # pre-check + both post-check attempts: button never consumed
            "colonize_button": [[_BUTTON], [_BUTTON], [_BUTTON]],
        }
    )
    sleeps: list[float] = []
    out = _colonize_executor(nav, sleeps).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "postcheck_mismatch"
    assert out[0].reason == "colonize_not_started"
    assert nav.clicks == [(100, 100), (200, 200)]
    assert len(sleeps) == 2  # waited before both post-check attempts


def test_colonize_postcheck_succeeds_on_retry() -> None:
    """Button still present on the first post-check but consumed on the retry."""
    nav = _FakeNavigator(
        find_returns={
            "colonizable_marker": [[_MARKER]],
            # pre-check, first post-check (still there), retry (consumed)
            "colonize_button": [[_BUTTON], [_BUTTON], []],
        }
    )
    sleeps: list[float] = []
    out = _colonize_executor(nav, sleeps).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "colonize_started"
    assert sleeps == [0.5, 0.5]


def test_colonize_targets_nearest_using_image_dims() -> None:
    """The marker nearest the *captured image* centre wins, not a hardcoded 1080p centre."""
    centre_1440p = TemplateMatch(x=1280, y=720, confidence=0.85)
    centre_1080p = TemplateMatch(x=960, y=540, confidence=0.9)
    nav = _FakeNavigator(
        image_size=(2560, 1440),
        find_returns={
            "colonizable_marker": [[centre_1080p, centre_1440p]],
            "colonize_button": [[_BUTTON], []],
        },
    )
    out = _colonize_executor(nav).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "colonize_started"
    assert nav.clicks[0] == (1280, 720)  # true centre of the 1440p capture


def test_colonize_degrades_when_backend_unavailable() -> None:
    """Capture returning None (no backend) → advisory result, never raises."""
    nav = _FakeNavigator(capture_returns=[None])
    out = _colonize_executor(nav).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "executed_no_nav"
    assert out[0].reason == "navigation_backend_unavailable"
    assert nav.clicks == []


def test_colonize_blocked_when_not_focused() -> None:
    """Focus guard: not focused → blocked, no capture/click at all."""
    nav = _FakeNavigator()
    out = ActionExecutor(focus_check=lambda: False, navigator=nav).execute(
        [_colonize_plan()], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "blocked"
    assert out[0].reason == "eu4_not_focused"
    assert nav.captures == []
    assert nav.clicks == []


def test_colonize_still_gated_without_confirm() -> None:
    """The safety gate is unchanged: no confirm → blocked, navigator untouched."""
    nav = _FakeNavigator()
    out = _colonize_executor(nav).execute([_colonize_plan()], mode=BotMode.SEMI_BOT)

    assert out[0].status == "blocked"
    assert out[0].reason == "confirmation_required"
    assert nav.captures == []
    assert nav.clicks == []


def test_colonize_assist_mode_is_advisory_only() -> None:
    """ASSIST mode never navigates, even for the colonize action."""
    nav = _FakeNavigator()
    out = _colonize_executor(nav).execute([_colonize_plan()], mode=BotMode.ASSIST)

    assert out[0].status == "advisory"
    assert nav.captures == []
    assert nav.clicks == []


def test_non_colonize_action_still_pauses() -> None:
    """A non-colonize action ignores the navigator and pauses via Space (unchanged)."""
    sent, sender = _recorder()
    nav = _FakeNavigator()
    out = ActionExecutor(key_sender=sender, focus_check=lambda: True, navigator=nav).execute(
        [_make_plan("economy_stabilize_budget")], mode=BotMode.SEMI_BOT, confirm=lambda _p: True
    )

    assert out[0].status == "executed"
    assert sent == ["space"]
    assert nav.captures == []  # navigator untouched for non-colonize actions
