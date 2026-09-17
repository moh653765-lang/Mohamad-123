import asyncio
import os

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    CallbackQuery,
)

BOT_TOKEN = os.environ["8026585919:AAFpDawu6-6Jcx1xpoNiwu6zo2YaxCP8F0M"]
ADMIN_ID = int(os.environ["8026585919"])

SERVER_ADDRESS = os.environ["SERVER_ADDRESS"]
SERVER_PORT = os.environ.get("SERVER_PORT", "443")

API_URL = "http://api:8000"

bot = Bot(8026585919:AAFpDawu6-6Jcx1xpoNiwu6zo2YaxCP8F0M)
dp = Dispatcher()


def menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ إنشاء حساب",
                    callback_data="create",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 الحسابات",
                    callback_data="list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 حذف حساب",
                    callback_data="delete",
                )
            ],
        ]
    )


def is_admin(message: Message):
    return message.from_user and message.from_user.id == ADMIN_ID


@dp.message(CommandStart())
async def start(message: Message):
    if not is_admin(message):
        await message.answer("⛔ غير مصرح لك باستخدام هذا البوت.")
        return

    await message.answer(
        "🤖 أهلاً بك في لوحة إدارة VLESS\n\n"
        "اختر العملية:",
        reply_markup=menu(),
    )


@dp.callback_query(F.data == "create")
async def create_start(callback: CallbackQuery):
    await callback.message.answer(
        "✏️ أرسل البيانات بهذا الشكل:\n\n"
        "`username days`\n\n"
        "مثال:\n"
        "`user01 30`",
        parse_mode="Markdown",
    )

    await callback.answer()


@dp.message()
async def create_account(message: Message):
    if not is_admin(message):
        return

    text = message.text.strip()

    if " " not in text:
        return

    parts = text.split()

    if len(parts) != 2:
        return

    username, days_text = parts

    try:
        days = int(days_text)
    except ValueError:
        return

    if days < 1 or days > 3650:
        await message.answer("❌ المدة يجب أن تكون بين 1 و3650 يوم.")
        return

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{API_URL}/users",
            json={
                "telegram_id": message.from_user.id,
                "username": username,
                "days": days,
            },
        )

    if response.status_code != 200:
        await message.answer("❌ حدث خطأ أثناء إنشاء الحساب.")
        return

    data = response.json()

    uuid = data["uuid"]

    config = (
        f"vless://{uuid}@{SERVER_ADDRESS}:{SERVER_PORT}"
        f"?type=tcp&security=tls"
        f"&encryption=none"
        f"#{username}"
    )

    await message.answer(
        "✅ تم إنشاء حساب VLESS\n\n"
        f"👤 الاسم: `{username}`\n"
        f"🆔 UUID: `{uuid}`\n"
        f"⏳ المدة: {days} يوم\n"
        f"📅 الانتهاء: `{data['expires_at']}`\n\n"
        "🔗 رابط VLESS:\n"
        f"`{config}`",
        parse_mode="Markdown",
        reply_markup=menu(),
    )


@dp.callback_query(F.data == "list")
async def list_users(callback: CallbackQuery):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{API_URL}/users")

    if response.status_code != 200:
        await callback.message.answer("❌ تعذر جلب الحسابات.")
        await callback.answer()
        return

    users = response.json()

    if not users:
        await callback.message.answer(
            "📭 لا توجد حسابات.",
            reply_markup=menu(),
        )
        await callback.answer()
        return

    text = "📋 الحسابات:\n\n"

    for user in users:
        text += (
            f"🆔 ID: `{user['id']}`\n"
            f"👤 {user['username']}\n"
            f"📅 {user['expires_at']}\n\n"
        )

    await callback.message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=menu(),
    )

    await callback.answer()


@dp.callback_query(F.data == "delete")
async def delete_help(callback: CallbackQuery):
    await callback.message.answer(
        "🗑 لحذف حساب أرسل:\n\n"
        "`delete ID`\n\n"
        "مثال:\n"
        "`delete 5`",
        parse_mode="Markdown",
    )

    await callback.answer()


async def delete_account(message: Message):
    parts = message.text.split()

    if len(parts) != 2:
        return

    try:
        user_id = int(parts[1])
    except ValueError:
        return

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.delete(
            f"{API_URL}/users/{user_id}"
        )

    if response.status_code == 200:
        await message.answer(
            "✅ تم حذف الحساب.",
            reply_markup=menu(),
        )
    else:
        await message.answer("❌ الحساب غير موجود.")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())