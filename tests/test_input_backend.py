"""Tests for InputBackend abstraction and StubBackend."""
from eu4_assistant_bot.execution.input_backend import StubBackend


class TestStubBackend:
    def test_click_records_call(self) -> None:
        backend = StubBackend()
        backend.click(100, 200)
        assert len(backend.calls) == 1
        assert backend.calls[0] == ("click", (100, 200))

    def test_right_click_records(self) -> None:
        backend = StubBackend()
        backend.right_click(50, 60)
        assert backend.calls[0] == ("right_click", (50, 60))

    def test_send_key_records(self) -> None:
        backend = StubBackend()
        backend.send_key("f1")
        assert backend.calls[0] == ("send_key", ("f1",))

    def test_type_text_records(self) -> None:
        backend = StubBackend()
        backend.type_text("hello")
        assert backend.calls[0] == ("type_text", ("hello",))

    def test_screenshot_returns_empty_bytes(self) -> None:
        backend = StubBackend()
        data = backend.screenshot_region(0, 0, 100, 100)
        assert data == b""
        assert backend.calls[0][0] == "screenshot_region"

    def test_locate_template_returns_configured_result(self) -> None:
        backend = StubBackend()
        backend.template_results["btn_recruit"] = (300, 400)
        pos = backend.locate_template("btn_recruit")
        assert pos == (300, 400)

    def test_locate_template_returns_none_when_not_configured(self) -> None:
        backend = StubBackend()
        pos = backend.locate_template("nonexistent")
        assert pos is None

    def test_drag_records_call(self) -> None:
        backend = StubBackend()
        backend.drag(10, 20, 30, 40)
        assert backend.calls[0] == ("drag", (10, 20, 30, 40))

    def test_multiple_calls_recorded_in_order(self) -> None:
        backend = StubBackend()
        backend.send_key("b")
        backend.click(100, 200)
        backend.send_key("escape")
        assert len(backend.calls) == 3
        assert backend.calls[0][0] == "send_key"
        assert backend.calls[1][0] == "click"
        assert backend.calls[2][0] == "send_key"
