from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards import main_menu_kb, radius_kb
from app.core.database import AsyncSessionLocal
from app.models.user import Executor, User

router = Router()


async def get_executor(telegram_id: int, db):
    result = await db.execute(
        select(Executor).join(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: Message):
    async with AsyncSessionLocal() as db:
        executor = await get_executor(message.from_user.id, db)
        if not executor:
            await message.answer("Сначала зарегистрируйтесь через /start")
            return
        radius = executor.search_radius_km or 5

    await message.answer(
        f"⚙️ <b>Настройки</b>\n\n"
        f"📏 Текущий радиус поиска: <b>{radius} км</b>\n\n"
        f"Выберите радиус:",
        parse_mode="HTML",
        reply_markup=radius_kb(radius),
    )


@router.callback_query(F.data.startswith("set_radius:"))
async def set_radius(callback: CallbackQuery):
    km = int(callback.data.split(":")[1])
    async with AsyncSessionLocal() as db:
        executor = await get_executor(callback.from_user.id, db)
        if not executor:
            await callback.answer("Сначала зарегистрируйтесь", show_alert=True)
            return
        executor.search_radius_km = km
        await db.commit()

    await callback.message.edit_text(
        f"⚙️ <b>Настройки</b>\n\n"
        f"📏 Радиус поиска установлен: <b>{km} км</b>\n\n"
        f"Выберите радиус:",
        parse_mode="HTML",
        reply_markup=radius_kb(km),
    )
    await callback.answer(f"Радиус {km} км сохранён")
