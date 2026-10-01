"""Настройки агента «unit-converter». Всё, что меняется между средами, — здесь.

Параметров памяти тут нет: агент по требованию работает без неё, поэтому
ни MONGODB_URI, ни TTL диалога не читаются и не используются.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "openai:gpt-5.5"


@dataclass(frozen=True)
class AgentConfig:
    """Конфигурация одного экземпляра агента."""

    model: str = DEFAULT_MODEL
    max_model_retries: int = 3
    max_tool_retries: int = 2

    # OpenAI-совместимый шлюз, через который ходят модели openai:*. Пустой
    # адрес — запросы уйдут в сам OpenAI, но ключ всё равно из llm_api_key.
    # Не OPENAI_API_KEY: тот нужен голосовым и картинкам, шлюз их не отдаёт.
    llm_base_url: str = ""
    llm_api_key: str = ""

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Собрать конфиг из окружения (.env подхватывается, если есть python-dotenv)."""
        _load_dotenv()
        return cls(
            model=os.environ.get("AGENT_MODEL", DEFAULT_MODEL),
            llm_base_url=os.environ.get("LLM_BASE_URL", ""),
            llm_api_key=os.environ.get("LLM_API_KEY", ""),
            max_model_retries=_int_env("AGENT_MAX_MODEL_RETRIES", 3),
            max_tool_retries=_int_env("AGENT_MAX_TOOL_RETRIES", 2),
        )

    def chat_model(self):
        """Модель для create_agent.

        openai:* собирается объектом с адресом и ключом шлюза; строки других
        провайдеров LangChain разберёт сам.
        """
        if not self.model.startswith("openai:"):
            return self.model
        from langchain.chat_models import init_chat_model

        return init_chat_model(
            self.model,
            base_url=self.llm_base_url or None,
            api_key=self.llm_api_key or None,
        )

    def require_api_key(self) -> None:
        """Проверить наличие ключа провайдера до первого запроса к модели."""
        key = "LLM_API_KEY"
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
