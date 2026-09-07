"""Реестр инструментов агента «unit-converter».

create_agent получает именно список TOOLS. Новый инструмент — новый модуль
в этом пакете плюс строка в TOOLS.
"""

from __future__ import annotations

from .convert import convert_units, list_units

TOOLS = [convert_units, list_units]

__all__ = ["TOOLS", "convert_units", "list_units"]
