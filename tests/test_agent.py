"""Смоук-тесты агента «unit-converter». Сеть не трогают."""

from __future__ import annotations

import pytest

import agent
from config import AgentConfig
from tools import TOOLS
from tools.convert import convert_units, list_units


def test_config_defaults_to_blueprint_model() -> None:
    assert AgentConfig().model == "anthropic:claude-sonnet-5"


def test_tools_are_registered() -> None:
    assert TOOLS, "список TOOLS пуст — агенту нечем работать"
    for item in TOOLS:
        assert item.name, "у инструмента нет имени"
        assert item.description, f"у инструмента {item.name} нет описания (docstring)"


def test_system_prompt_is_not_empty() -> None:
    assert agent.SYSTEM_PROMPT.strip()


def test_agent_builds() -> None:
    built = agent.build_agent(AgentConfig())
    assert built is not None


def test_agent_has_no_memory() -> None:
    """Памяти быть не должно: ни модуля памяти, ни аргумента чекпоинтера."""
    import inspect

    assert "checkpointer" not in inspect.signature(agent.build_agent).parameters
    with pytest.raises(ImportError):
        __import__("memory")


def call(tool, **kwargs) -> str:
    return tool.invoke(kwargs)


@pytest.mark.parametrize(
    "value, src, dst, expected",
    [
        (1.0, "km", "m", "1000"),
        (1.0, "миля", "км", "1.609344"),
        (100.0, "°C", "F", "212"),
        (0.0, "C", "K", "273.15"),
        (1.0, "кг", "фунт", "2.204622622"),
        (1.0, "л", "мл", "1000"),
        (100.0, "км/ч", "м/с", "27.77777778"),
        (1.0, "га", "м2", "10000"),
        (1.0, "ч", "мин", "60"),
        (1.0, "атм", "па", "101325"),
        (1.0, "квт·ч", "дж", "3600000"),
        (1.0, "гб", "мб", "1000"),
        (180.0, "градус", "рад", "3.14159"),
    ],
)
def test_known_conversions(value: float, src: str, dst: str, expected: str) -> None:
    result = call(convert_units, value=value, from_unit=src, to_unit=dst)
    assert expected in result, result


def test_roundtrip_is_stable() -> None:
    result = call(convert_units, value=37.0, from_unit="C", to_unit="F")
    assert "98.6" in result


def test_unknown_unit_reports_error() -> None:
    result = call(convert_units, value=1.0, from_unit="попугай", to_unit="м")
    assert "Не понял" in result


def test_mismatched_categories_report_error() -> None:
    result = call(convert_units, value=1.0, from_unit="кг", to_unit="м")
    assert "не переводятся" in result


def test_list_units_lists_categories_and_units() -> None:
    assert "длина" in call(list_units, category="")
    assert "kg" in call(list_units, category="масса")
    assert "c" in call(list_units, category="температура")
