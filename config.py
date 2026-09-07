"""Настройки агента «unit-converter». Всё, что меняется между средами, — здесь.

Параметров памяти тут нет: агент по требованию работает без неё, поэтому
ни MONGODB_URI, ни TTL диалога не читаются и не используются.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "anthropic:claude-sonnet-5"


@dataclass(frozen=True)
class AgentConfig:
    """Конфигурация одного экземпляра агента."""

    model: str = DEFAULT_MODEL
    max_model_retries: int = 3
    max_tool_retries: int = 2

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Собрать конфиг из окружения (.env подхватывается, если есть python-dotenv)."""
        _load_dotenv()
        return cls(
            model=os.environ.get("AGENT_MODEL", DEFAULT_MODEL),
            max_model_retries=_int_env("AGENT_MAX_MODEL_RETRIES", 3),
            max_tool_retries=_int_env("AGENT_MAX_TOOL_RETRIES", 2),
        )

    def require_api_key(self) -> None:
        """Проверить наличие ключа провайдера до первого запроса к модели."""
        key = "ANTHROPIC_API_KEY"
        if key and not os.environ.get(key):
            raise RuntimeError(
                f"Не задана переменная окружения {key}. "
                "Скопируй .env.example в .env и заполни её."
            )


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()
