"""Отправка Telegram-сообщений из бэкенда (например, при смене статуса задания)."""
from aiogram import Bot

from app.core.config import settings

_bot: Bot | None = None


def get_bot() -> Bot:
    global _bot
    if _bot is None:
        _bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    return _bot


async def notify_telegram(telegram_id: int, text: str) -> bool:
    try:
        bot = get_bot()
        await bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
        return True
    except Exception:
        return False
