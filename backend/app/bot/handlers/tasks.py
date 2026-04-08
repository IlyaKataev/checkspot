import io
import os
import uuid
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Location, Message, PhotoSize
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.bot.keyboards import (
    after_submit_kb,
    main_menu_kb,
    photo_kb,
    request_location_kb,
    task_kb,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.campaign import Campaign, CampaignStatus
from app.models.task import Notification, Task, TaskReport, TaskStatus
from app.models.user import Client, Executor, User

import math

router = Router()

TASK_TIME_LIMIT_MINUTES = 30


def haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class TaskState(StatesGroup):
    waiting_location = State()
    task_in_progress = State()
    waiting_photo = State()


async def get_executor(telegram_id: int, db) -> Executor | None:
    result = await db.execute(
        select(Executor).join(User).where(User.telegram_id == telegram_id)
        .options(selectinload(Executor.user))
    )
    return result.scalar_one_or_none()


# ── Найти задания ────────────────────────────────────────────────────────────

@router.message(F.text == "🔍 Найти задания")
async def find_tasks_start(message: Message, state: FSMContext):
    await message.answer(
        "📍 Отправьте вашу геолокацию, чтобы найти задания рядом:",
        reply_markup=request_location_kb(),
    )
    await state.set_state(TaskState.waiting_location)


@router.message(TaskState.waiting_location, F.location)
async def got_location(message: Message, state: FSMContext):
    loc: Location = message.location
    lat, lng = loc.latitude, loc.longitude

    await state.update_data(lat=lat, lng=lng)

    async with AsyncSessionLocal() as db:
        executor = await get_executor(message.from_user.id, db)
        if executor:
            executor.lat = lat
            executor.lng = lng
            executor.last_seen_at = datetime.now(timezone.utc)
            await db.commit()

        result = await db.execute(
            select(Task)
            .join(Campaign)
            .where(
                Task.status == TaskStatus.available,
                Campaign.status == CampaignStatus.active,
                Task.lat.isnot(None),
                Task.lng.isnot(None),
            )
            .options(selectinload(Task.campaign))
        )
        tasks = result.scalars().all()

    radius_m = (executor.search_radius_km or 5) * 1000 if executor else 5000

    nearby = []
    for task in tasks:
        dist = haversine_m(lat, lng, float(task.lat), float(task.lng))
        if dist <= radius_m:
            nearby.append((task, dist))

    nearby.sort(key=lambda x: x[1])

    await state.clear()

    radius_km = radius_m // 1000
    if not nearby:
        await message.answer(
            f"😔 Рядом с вами (в радиусе {radius_km} км) нет доступных заданий.\n\n"
            "Попробуйте увеличить радиус в ⚙️ Настройках или зайдите позже.",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(
        f"🔍 Найдено заданий: <b>{len(nearby)}</b>",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )

    for task, dist in nearby[:5]:  # показываем не более 5
        text = (
            f"📍 <b>{task.address}</b>\n"
            f"🏷 Категория: {task.campaign.category}\n"
            f"📏 Расстояние: {int(dist)} м\n"
            f"💰 Оплата: <b>{task.campaign.price_per_task:.0f} ₽</b>\n"
            f"⏱ Время на выполнение: {TASK_TIME_LIMIT_MINUTES} мин"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=task_kb(task.id))


# ── Взять задание ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("accept:"))
async def accept_task(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as db:
        executor = await get_executor(callback.from_user.id, db)
        if not executor:
            await callback.answer("Сначала зарегистрируйтесь через /start", show_alert=True)
            return

        task = await db.get(Task, task_id, options=[selectinload(Task.campaign)])
        if not task:
            await callback.answer("Задание не найдено", show_alert=True)
            return
        if task.status != TaskStatus.available:
            await callback.answer("Задание уже занято", show_alert=True)
            return

        # Проверяем нет ли уже активного задания
        active = await db.execute(
            select(Task).where(
                Task.executor_id == executor.id,
                Task.status == TaskStatus.in_progress,
            )
        )
        if active.scalar_one_or_none():
            await callback.answer("У вас уже есть активное задание", show_alert=True)
            return

        now = datetime.now(timezone.utc)
        task.status = TaskStatus.in_progress
        task.executor_id = executor.id
        task.accepted_at = now
        task.deadline_at = now + timedelta(minutes=TASK_TIME_LIMIT_MINUTES)
        await db.commit()

        category = task.campaign.category
        address = task.address
        price = float(task.campaign.price_per_task)

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        f"✅ <b>Задание принято!</b>\n\n"
        f"📍 Адрес: {address}\n"
        f"🏷 Категория: {category}\n"
        f"💰 Оплата: {price:.0f} ₽\n"
        f"⏱ У вас есть <b>{TASK_TIME_LIMIT_MINUTES} минут</b>\n\n"
        f"📸 Сфотографируйте полку с категорией <b>«{category}»</b>.\n\n"
        f"<b>Требования к фото:</b>\n"
        f"• Полка видна целиком\n"
        f"• Товары и ценники читаемы\n"
        f"• Фото сделано прямо сейчас (не из галереи)\n\n"
        f"Когда будете готовы — просто пришлите фото в чат.",
        parse_mode="HTML",
        reply_markup=photo_kb(),
    )

    await state.update_data(task_id=task_id)
    await state.set_state(TaskState.waiting_photo)
    await callback.answer()


@router.message(F.text == "❌ Отменить задание")
async def cancel_task(message: Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("task_id")

    if task_id:
        async with AsyncSessionLocal() as db:
            task = await db.get(Task, task_id)
            if task and task.status == TaskStatus.in_progress:
                task.status = TaskStatus.available
                task.executor_id = None
                task.accepted_at = None
                task.deadline_at = None
                await db.commit()

    await state.clear()
    await message.answer("Задание отменено.", reply_markup=main_menu_kb())


# ── Загрузка фото ────────────────────────────────────────────────────────────

@router.message(TaskState.waiting_photo, F.photo)
async def got_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    task_id = data.get("task_id")

    if not task_id:
        await message.answer("Что-то пошло не так. Начните заново.", reply_markup=main_menu_kb())
        await state.clear()
        return

    await message.answer("⏳ Получаю фото...", reply_markup=main_menu_kb())

    # Скачиваем фото
    photo: PhotoSize = message.photo[-1]  # берём максимальное качество
    file = await bot.get_file(photo.file_id)
    file_bytes = await bot.download_file(file.file_path)

    os.makedirs(settings.MEDIA_DIR, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(settings.MEDIA_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(file_bytes.read())

    async with AsyncSessionLocal() as db:
        executor = await get_executor(message.from_user.id, db)
        if not executor:
            await message.answer("Ошибка: исполнитель не найден.", reply_markup=main_menu_kb())
            await state.clear()
            return

        task = await db.get(Task, task_id, options=[selectinload(Task.campaign)])
        if not task or task.executor_id != executor.id or task.status != TaskStatus.in_progress:
            await message.answer("Задание не активно.", reply_markup=main_menu_kb())
            await state.clear()
            return

        # Проверка таймера
        if task.deadline_at and datetime.now(timezone.utc) > task.deadline_at.replace(tzinfo=timezone.utc):
            task.status = TaskStatus.available
            task.executor_id = None
            task.accepted_at = None
            task.deadline_at = None
            await db.commit()
            await message.answer(
                "⏰ Время на задание истекло. Оно снова доступно для других.\n"
                "Возьмите другое задание.",
                reply_markup=main_menu_kb(),
            )
            await state.clear()
            return

        # Сохраняем отчёт
        report = TaskReport(
            task_id=task.id,
            executor_id=executor.id,
            photo_path=filename,
            photo_taken_at=datetime.now(timezone.utc),
        )
        db.add(report)
        task.status = TaskStatus.pending_review
        await db.flush()

        # Уведомляем заказчика
        campaign = task.campaign
        client_res = await db.execute(select(Client).where(Client.id == campaign.client_id))
        client = client_res.scalar_one_or_none()
        if client:
            notif = Notification(
                user_id=client.user_id,
                title="Новое фото на проверку",
                body=f"Фото по адресу «{task.address}» ожидает модерации",
                meta={"task_id": task.id, "campaign_id": campaign.id},
            )
            db.add(notif)

        await db.commit()

    await state.clear()
    await message.answer(
        "✅ <b>Фото отправлено на проверку!</b>\n\n"
        "Заказчик проверит его в ближайшее время.\n"
        "Как только фото будет проверено — вы получите уведомление.\n\n"
        "💡 Деньги зачислятся после одобрения.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )


@router.message(TaskState.waiting_photo)
async def wrong_content_in_photo_state(message: Message):
    await message.answer(
        "📸 Пришлите фото полки. Документы и файлы не принимаются.",
        reply_markup=photo_kb(),
    )


# ── Callback-кнопки ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "find_tasks")
async def cb_find_tasks(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await find_tasks_start(callback.message, state)
