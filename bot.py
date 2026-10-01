"""Telegram-бот агента «unit-converter» — то, что крутится в контейнере.

Запуск:  python bot.py

Нужно в окружении:
    TELEGRAM_BOT_TOKEN — токен от @BotFather
    ALLOWED_USER_IDS   — кому разрешено писать боту, через запятую
    LLM_API_KEY        — ключ доступа к шлюзу моделей
    LLM_BASE_URL       — адрес OpenAI-совместимого шлюза

Памяти нет: каждое сообщение уходит в агента отдельным запросом, без
чекпоинтера и без истории. Поэтому здесь нет ни thread_id, ни /reset.
"""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from agent import build_agent
from config import AgentConfig

TELEGRAM_LIMIT = 4096

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("unit-converter")

dp = Dispatcher()

# "*" = бот открыт для всех.
# Пустой список = бот никого не пускает, но подскажет каждому его ID.
_ALLOWED_RAW = os.environ.get("ALLOWED_USER_IDS", "").replace(" ", "")
ALLOW_EVERYONE = "*" in _ALLOWED_RAW
ALLOWED = {int(x) for x in _ALLOWED_RAW.split(",") if x and x != "*"}

_config = AgentConfig.from_env()
_agent = None

GREETING = (
    "unit-converter на связи.\n\n"
    "Перевожу числа между единицами измерения: длина, масса, температура,\n"
    "объём, скорость, площадь, время, давление, энергия, мощность, данные,\n"
    "углы, частота.\n\n"
    "Примеры:\n"
    "• 12 км в милях\n"
    "• 451 °F в цельсиях\n"
    "• 2.5 фунта в граммы\n"
    "• 100 миль в час в м/с\n\n"
    "Истории диалога я не храню — каждое сообщение считается отдельно."
)


def chunks(text: str) -> list[str]:
    """Режет длинный ответ на куски, которые Telegram согласится отправить."""
    parts = [text[i : i + TELEGRAM_LIMIT] for i in range(0, len(text), TELEGRAM_LIMIT)]
    return parts or ["(пустой ответ)"]


def is_allowed(message: Message) -> bool:
    if ALLOW_EVERYONE:
        return True
    return message.from_user is not None and message.from_user.id in ALLOWED


@dp.message(CommandStart())
async def on_start(message: Message) -> None:
    if not is_allowed(message):
        await message.answer(
            "Доступ закрыт.\n\n"
            f"Ваш Telegram ID: {message.from_user.id}\n"
            "Добавьте его в ALLOWED_USER_IDS и перезапустите бота."
        )
        return
    await message.answer(GREETING)


@dp.message(F.text)
async def on_text(message: Message) -> None:
    if not is_allowed(message):
        await message.answer(f"Доступ закрыт. Ваш Telegram ID: {message.from_user.id}")
        return

    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        try:
            # Ни thread_id, ни истории: агент видит только текущее сообщение.
            result = await _agent.ainvoke(
                {"messages": [{"role": "user", "content": message.text}]}
            )
            answer = result["messages"][-1].text
        except Exception:
            log.exception("Ошибка при обработке сообщения")
            answer = "Что-то пошло не так при обращении к модели. Подробности в логе."

    for part in chunks(answer):
        await message.answer(part)


async def main() -> None:
    global _agent

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "Нет TELEGRAM_BOT_TOKEN. Получите токен у @BotFather и положите его "
            "в .env рядом с docker-compose.yml."
        )
    _config.require_api_key()
    if ALLOW_EVERYONE:
        log.warning("ALLOWED_USER_IDS='*' — бот открыт для всех желающих.")
    elif not ALLOWED:
        log.warning("ALLOWED_USER_IDS пуст — бот никого не пустит, но покажет каждому его ID.")

    _agent = build_agent(_config)
    log.info("Память отключена: агент не хранит историю диалогов.")

    bot = Bot(token=token)
    me = await bot.get_me()
    log.info("Бот @%s запущен, модель %s", me.username, _config.model)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
