"""Test del servizio di ispezione/modifica dei parametri dei nodi."""

from __future__ import annotations

import pytest

from app.adapters.ros_cli import CommandResult
from app.core.config import Settings
from app.services.param_service import ParamService, ParamWriteNotConfirmedError
from tests.fakes import FakeRosCommandRunner


def _service(responses: dict[tuple[str, ...], CommandResult]) -> ParamService:
    """Crea un ParamService con un runner programmato."""
    return ParamService(runner=FakeRosCommandRunner(responses), settings=Settings())


def test_list_params_parses_names() -> None:
    """L'elenco parametri deve essere estratto e ordinato."""
    service = _service(
        {
            ("param", "list", "/talker"): CommandResult(
                ["param", "list", "/talker"], 0, "  use_sim_time\n  alpha\n", ""
            )
        }
    )
    result = service.list_params("/talker")
    assert result.available is True
    assert result.params == ["alpha", "use_sim_time"]


def test_list_params_unavailable_on_error() -> None:
    """Un fallimento della CLI deve risultare available=False."""
    service = _service(
        {
            ("param", "list", "/talker"): CommandResult(
                ["param", "list", "/talker"], 1, "", "boom"
            )
        }
    )
    result = service.list_params("/talker")
    assert result.available is False


def test_get_param_extracts_value() -> None:
    """Il valore deve essere estratto dalla forma '<Tipo> value is: X'."""
    service = _service(
        {
            ("param", "get", "/talker", "count"): CommandResult(
                ["param", "get", "/talker", "count"], 0, "Integer value is: 42\n", ""
            )
        }
    )
    result = service.get_param("/talker", "count")
    assert result.available is True
    assert result.value == "42"


def test_set_param_without_confirm_raises() -> None:
    """Senza conferma la scrittura deve essere rifiutata (e non eseguita)."""
    service = _service({})
    with pytest.raises(ParamWriteNotConfirmedError):
        service.set_param("/talker", "count", "7", confirm=False)


def test_set_param_with_confirm_succeeds() -> None:
    """Con conferma e CLI ok la scrittura deve risultare riuscita."""
    service = _service(
        {
            ("param", "set", "/talker", "count", "7"): CommandResult(
                ["param", "set", "/talker", "count", "7"],
                0,
                "Set parameter successful",
                "",
            )
        }
    )
    result = service.set_param("/talker", "count", "7", confirm=True)
    assert result.success is True
    assert result.value == "7"
