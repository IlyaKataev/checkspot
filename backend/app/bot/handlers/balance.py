from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.bot.keyboards import main_menu_kb, payout_confirm_kb
from app.core.database import AsyncSessionLocal
from app.models.task import Payout, PayoutStatus, Task, TaskStatus
from app.models.user import Executor, User

router = Router()


async def get_executor(telegram_id: int, db):
    result = await db.execute(
        select(Executor).join(User).where(User.telegram_id == telegram_id)
        .options(selectinload(Executor.user))
    )
    return result.scalar_one_or_none()


@router.message(F.text == "💰 Мой баланс")
async def show_balance(message: Message):
    async with AsyncSessionLocal() as db:
        executor = await get_executor(message.from_user.id, db)
        if not executor:
            await message.answer("Сначала зарегистрируйтесь через /start")
            return

        balance = float(executor.balance)
        completed = executor.completed_tasks

        # Ожидающие выплаты
        result = await db.execute(
            select(Payout).where(
                Payout.executor_id == executor.id,
                Payout.status == PayoutStatus.pending,
            )
        )
        pending = result.scalars().all()
        pending_total = sum(float(p.amount) for p in pending)

    lines = [
        f"💰 <b>Баланс: {balance:.0f} ₽</b>",
        f"✅ Выполнено заданий: {completed}",
    ]
    if pending_total > 0:
        lines.append(f"⏳ В обработке: {pending_total:.0f} ₽")
    if balance > 0:
        lines.append(f"\nМинимальная сумма для вывода: 100 ₽")

    text = "\n".join(lines)

    if balance >= 100:
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=payout_confirm_kb(balance),
        )
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=main_menu_kb())


@router.callback_query(F.data == "balance")
async def cb_balance(callback: CallbackQuery):
    await callback.answer()
    await show_balance(callback.message)


@router.callback_query(F.data == "confirm_payout")
async def confirm_payout(callback: CallbackQuery):
    async with AsyncSessionLocal() as db:
        executor = await get_executor(callback.from_user.id, db)
        if not executor:
            await callback.answer("Исполнитель не найден", show_alert=True)
            return

        balance = float(executor.balance)
        if balance < 100:
            await callback.answer("Недостаточно средств", show_alert=True)
            return

        payout = Payout(
            executor_id=executor.id,
            amount=balance,
            phone=executor.user.phone,
            status=PayoutStatus.pending,
        )
        db.add(payout)
        executor.balance = 0
        await db.commit()

    await callback.message.edit_text(
        f"✅ <b>Заявка на вывод принята!</b>\n\n"
        f"Сумма: {balance:.0f} ₽\n"
        f"Телефон: {executor.user.phone}\n\n"
        f"Перевод поступит в течение 1–3 часов.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_payout")
async def cancel_payout(callback: CallbackQuery):
    await callback.message.edit_reply_markup()
    await callback.answer("Отменено")


@router.message(F.text == "📋 История")
async def show_history(message: Message):
    async with AsyncSessionLocal() as db:
        executor = await get_executor(message.from_user.id, db)
        if not executor:
            await message.answer("Сначала зарегистрируйтесь через /start")
            return

        result = await db.execute(
            select(Task)
            .where(
                Task.executor_id == executor.id,
                Task.status.in_([TaskStatus.completed, TaskStatus.rejected]),
            )
            .options(selectinload(Task.campaign))
            .order_by(Task.completed_at.desc())
            .limit(10)
        )
        tasks = result.scalars().all()

    if not tasks:
        await message.answer("У вас пока нет выполненных заданий.", reply_markup=main_menu_kb())
        return

    lines = ["📋 <b>Последние задания:</b>\n"]
    for t in tasks:
        icon = "✅" if t.status == TaskStatus.completed else "❌"
        price = float(t.campaign.price_per_task) if t.status == TaskStatus.completed else 0
        date = t.completed_at.strftime("%d.%m %H:%M") if t.completed_at else "—"
        lines.append(f"{icon} {t.address} — {price:.0f} ₽ ({date})")

    await message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu_kb())


@router.message(F.text == "❓ Поддержка")
async def support(message: Message):
    await message.answer(
        "❓ <b>Поддержка</b>\n\n"
        "Напишите ваш вопрос или опишите проблему — мы ответим в течение нескольких часов.\n\n"
        "Или напишите напрямую: @checkspot_support",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
