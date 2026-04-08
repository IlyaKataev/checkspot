from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Contact, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import agree_kb, main_menu_kb, request_location_kb, request_phone_kb
from app.core.database import AsyncSessionLocal
from app.models.user import Executor, User, UserRole

router = Router()

AGREEMENT_TEXT = (
    "📋 <b>Условия работы:</b>\n\n"
    "• Вы получаете деньги за фото полок в магазинах\n"
    "• 150–300 ₽ за одно задание\n"
    "• Фото делается прямо сейчас (только с камеры)\n"
    "• За некачественные фото деньги не начисляются\n"
    "• Вывод от 100 ₽ на ваш номер телефона\n\n"
    "Нажимая «Согласен», вы принимаете условия использования сервиса."
)


class OnboardingState(StatesGroup):
    waiting_phone = State()
    waiting_agreement = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

    if user and user.agreed_at:
        await message.answer(
            f"👋 С возвращением, {user.name or 'друг'}!",
            reply_markup=main_menu_kb(),
        )
        return

    await message.answer(
        "👋 Привет! Я <b>CheckSpot Bot</b>.\n\n"
        "Помогаю зарабатывать на фотографиях полок в магазинах.\n\n"
        "💰 <b>150–300 ₽</b> за одно фото\n"
        "⏱ <b>30 минут</b> на задание\n"
        "📍 Задания рядом с вами\n\n"
        "Для начала поделитесь вашим номером телефона:",
        parse_mode="HTML",
        reply_markup=request_phone_kb(),
    )
    await state.set_state(OnboardingState.waiting_phone)


@router.message(OnboardingState.waiting_phone, F.contact)
async def got_phone(message: Message, state: FSMContext):
    contact: Contact = message.contact
    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await state.update_data(phone=phone)
    await message.answer(AGREEMENT_TEXT, parse_mode="HTML", reply_markup=agree_kb())
    await state.set_state(OnboardingState.waiting_agreement)


@router.message(OnboardingState.waiting_phone)
async def wrong_phone(message: Message):
    await message.answer(
        "Пожалуйста, используйте кнопку «📱 Поделиться номером» ниже.",
        reply_markup=request_phone_kb(),
    )


from aiogram.types import CallbackQuery


@router.callback_query(OnboardingState.waiting_agreement, F.data == "agree")
async def agreed(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone", "")

    tg_user = callback.from_user
    async with AsyncSessionLocal() as db:
        # Проверяем нет ли уже такого пользователя
        result = await db.execute(select(User).where(User.telegram_id == tg_user.id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                role=UserRole.executor,
                telegram_id=tg_user.id,
                telegram_username=tg_user.username,
                name=tg_user.full_name,
                phone=phone,
                agreed_at=datetime.now(timezone.utc),
            )
            db.add(user)
            await db.flush()

            executor = Executor(user_id=user.id)
            db.add(executor)
            await db.commit()
        else:
            user.phone = phone
            user.agreed_at = datetime.now(timezone.utc)
            await db.commit()

    await callback.message.edit_text("✅ Регистрация завершена!")
    await callback.message.answer(
        "🎉 Отлично! Теперь вы можете брать задания.\n\n"
        "Нажмите <b>«🔍 Найти задания»</b> — бот покажет задания рядом с вами.",
        parse_mode="HTML",
        reply_markup=main_menu_kb(),
    )
    await state.clear()
    await callback.answer()


@router.callback_query(OnboardingState.waiting_agreement, F.data == "disagree")
async def disagreed(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Жаль. Если передумаете — введите /start снова."
    )
    await state.clear()
    await callback.answer()
