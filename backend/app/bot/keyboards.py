from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔍 Найти задания")
    kb.button(text="💰 Мой баланс")
    kb.button(text="📋 История")
    kb.button(text="❓ Поддержка")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)


def request_phone_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📱 Поделиться номером", request_contact=True)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def request_location_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📍 Отправить геолокацию", request_location=True)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def agree_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласен", callback_data="agree")
    builder.button(text="❌ Отказаться", callback_data="disagree")
    return builder.as_markup()


def task_kb(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Взять задание", callback_data=f"accept:{task_id}")
    return builder.as_markup()


def photo_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="❌ Отменить задание")
    return kb.as_markup(resize_keyboard=True)


def after_submit_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти ещё задания", callback_data="find_tasks")
    builder.button(text="💰 Мой баланс", callback_data="balance")
    builder.adjust(1)
    return builder.as_markup()


def payout_confirm_kb(amount: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"✅ Вывести {amount:.0f} ₽", callback_data="confirm_payout")
    builder.button(text="❌ Отмена", callback_data="cancel_payout")
    builder.adjust(1)
    return builder.as_markup()


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
