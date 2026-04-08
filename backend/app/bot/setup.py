from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def setup_routers():
    from app.bot.handlers.onboarding import router as onboarding_router
    from app.bot.handlers.tasks import router as tasks_router
    from app.bot.handlers.balance import router as balance_router
    from app.bot.handlers.settings import router as settings_router

    dp.include_router(onboarding_router)
    dp.include_router(tasks_router)
    dp.include_router(balance_router)
    dp.include_router(settings_router)
