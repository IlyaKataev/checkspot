import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine
from app.models import *  # noqa: регистрируем модели


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from app.bot.setup import bot, dp, setup_routers
    from app.services.task_scheduler import scheduler_loop
    setup_routers()

    async def start_bot():
        try:
            if settings.WEBHOOK_URL:
                webhook_url = f"{settings.WEBHOOK_URL}/bot/webhook"
                await bot.set_webhook(webhook_url)
                print(f"Bot webhook set: {webhook_url}")
            else:
                await bot.delete_webhook()
                await dp.start_polling(bot, handle_signals=False)
                print("Bot polling started")
        except Exception as e:
            print(f"Warning: bot startup error: {e}")

    asyncio.create_task(start_bot())
    asyncio.create_task(scheduler_loop())

    yield

    # Завершение
    try:
        if not settings.WEBHOOK_URL:
            await dp.stop_polling()
        await bot.session.close()
    except Exception:
        pass


app = FastAPI(title="CheckSpot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика (фото)
os.makedirs(settings.MEDIA_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

# Роуты
from app.api import auth, campaigns, tasks, executor, notifications, admin

app.include_router(auth.router, prefix="/api")
app.include_router(campaigns.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(executor.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


# Telegram webhook endpoint (для продакшена)
@app.post("/bot/webhook")
async def bot_webhook(request: Request):
    from aiogram.types import Update
    from app.bot.setup import bot, dp
    body = await request.body()
    update = Update.model_validate_json(body)
    await dp.feed_update(bot=bot, update=update)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}
