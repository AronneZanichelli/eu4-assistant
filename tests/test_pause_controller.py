from eu4_assistant_bot.models import GameSnapshot, DiplomacyState, RiskState
from eu4_assistant_bot.pause_controller import PauseController, PauseTrigger


def _snap(rebels: float = 0.0, truces: list | None = None) -> GameSnapshot:
    snap = GameSnapshot.empty("POR")
    snap.risk = RiskState(rebels=rebels, coalition=0.0)
    snap.diplomacy = DiplomacyState(truces=truces or [], alliances=[], ae_map={})
    return snap


def test_rebels_imminent_triggers_pause():
    paused = []
    ctrl = PauseController(send_pause_fn=lambda: None, on_pause=paused.append)
    events = ctrl.update(_snap(rebels=0.8))
    assert len(events) == 1
    assert events[0].trigger == PauseTrigger.REBELS_IMMINENT


def test_rebels_below_threshold_no_pause():
    paused = []
    ctrl = PauseController(send_pause_fn=lambda: None, on_pause=paused.append)
    events = ctrl.update(_snap(rebels=0.3))
    assert events == []


def test_rebels_trigger_not_repeated():
    """Stessa condizione non deve generare più di un evento consecutivo."""
    paused = []
    ctrl = PauseController(send_pause_fn=lambda: None, on_pause=paused.append)
    ctrl.update(_snap(rebels=0.9))
    ctrl.update(_snap(rebels=0.9))
    assert len(paused) == 1


def test_rebels_trigger_resets_when_condition_clears():
    paused = []
    ctrl = PauseController(send_pause_fn=lambda: None, on_pause=paused.append)
    ctrl.update(_snap(rebels=0.9))   # trigger
    ctrl.update(_snap(rebels=0.1))   # condition cleared
    ctrl.update(_snap(rebels=0.9))   # trigger again
    assert len(paused) == 2


def test_war_declared_triggers_pause():
    paused = []
    ctrl = PauseController(send_pause_fn=lambda: None, on_pause=paused.append)
    ctrl.update(_snap(truces=[]))                          # stato iniziale: no guerra
    events = ctrl.update(_snap(truces=[{"who": "FRA"}]))   # nuova truce → guerra
    assert any(e.trigger == PauseTrigger.WAR_DECLARED for e in events)


def test_war_trigger_not_repeated():
    paused = []
    ctrl = PauseController(send_pause_fn=lambda: None, on_pause=paused.append)
    ctrl.update(_snap(truces=[]))
    ctrl.update(_snap(truces=[{"who": "FRA"}]))  # prima guerra
    ctrl.update(_snap(truces=[{"who": "FRA"}]))  # stesso stato
    war_events = [e for e in paused if e.trigger == PauseTrigger.WAR_DECLARED]
    assert len(war_events) == 1


def test_reset_clears_state():
    paused = []
    ctrl = PauseController(send_pause_fn=lambda: None, on_pause=paused.append)
    ctrl.update(_snap(rebels=0.9))
    ctrl.reset()
    events = ctrl.update(_snap(rebels=0.9))
    assert len(events) == 1   # trigger di nuovo dopo reset


def test_send_pause_called_on_trigger():
    called = []
    ctrl = PauseController(send_pause_fn=lambda: called.append(1))
    ctrl.update(_snap(rebels=0.9))
    assert len(called) == 1
