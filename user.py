import logging
import random
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from keyboards import (
    main_menu_keyboard, back_keyboard, cancel_keyboard,
    tasks_list_keyboard, channels_sub_keyboard, payment_methods_keyboard
)
from config import ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)


class WithdrawStates(StatesGroup):
    choosing_method = State()
    waiting_amount = State()
    waiting_wallet = State()


async def check_subscriptions(bot: Bot, user_id: int) -> bool:
    channels = await db.get_active_channels()
    if not channels:
        return True
    for ch in channels:
        ch_type = ch["channel_type"]
        if ch_type == "link":
            continue
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ["left", "kicked", "banned"]:
                return False
        except Exception:
            pass
    return True


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or "Foydalanuvchi"

    referred_by = None
    args = message.text.split()
    if len(args) > 1:
        try:
            ref_id = int(args[1])
            if ref_id != user_id:
                referred_by = ref_id
        except ValueError:
            pass

    user = await db.get_user(user_id)
    is_new = user is None

    if is_new:
        await db.create_user(user_id, username, full_name, referred_by)
        if referred_by:
            ref_user = await db.get_user(referred_by)
            if ref_user and not ref_user["is_banned"]:
                bonus = int(await db.get_setting("referral_bonus") or 180)
                await db.update_balance(referred_by, bonus)
                await db.execute_referral_count(referred_by)
                try:
                    await bot.send_message(
                        referred_by,
                        f"🎉 Yangi referal! <b>{full_name}</b> havolangiz orqali qo'shildi!\n"
                        f"💰 Sizga <b>{bonus} so'm</b> qo'shildi!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    await db.update_last_active(user_id)
    user = await db.get_user(user_id)
    if user and user["is_banned"]:
        await message.answer("🚫 Siz bloklangansiz.")
        return

    subscribed = await check_subscriptions(bot, user_id)
    if not subscribed:
        channels = await db.get_active_channels()
        await message.answer(
            "📢 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
            reply_markup=channels_sub_keyboard(channels)
        )
        return

    is_adm = await db.is_admin(user_id)
    await message.answer(
        f"👋 Xush kelibsiz, <b>{full_name}</b>!\n\n"
        "💡 Referal tizimimizdan foydalaning va pul ishlang!\n"
        "📌 Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu_keyboard(is_adm),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "check_subscription")
async def check_sub_callback(call: CallbackQuery, bot: Bot):
    await db.update_last_active(call.from_user.id)
    subscribed = await check_subscriptions(bot, call.from_user.id)
    if subscribed:
        is_adm = await db.is_admin(call.from_user.id)
        await call.message.edit_reply_markup()
        await call.message.answer(
            "✅ Rahmat! Endi botdan foydalanishingiz mumkin.",
            reply_markup=main_menu_keyboard(is_adm)
        )
    else:
        await call.answer("❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)


# ===================== PUL ISHLASH =====================

@router.message(F.text == "💸 Pul ishlash")
async def pul_ishlash(message: Message, bot: Bot):
    await db.update_last_active(message.from_user.id)
    user_id = message.from_user.id
    bonus = await db.get_setting("referral_bonus") or "180"
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    await message.answer(
        f"💸 <b>Pul ishlash</b>\n\n"
        f"👥 Har bir referal uchun: <b>{bonus} so'm</b>\n\n"
        f"📌 <b>Qanday ishlaydi?</b>\n"
        f"1️⃣ Referal havolangizni ulashing\n"
        f"2️⃣ Do'stingiz botga kiradi\n"
        f"3️⃣ Siz avtomatik bonus olasiz!\n\n"
        f"🔗 <b>Sizning referal havolangiz:</b>\n"
        f"<code>{ref_link}</code>",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )


# ===================== HISOBIM =====================

@router.message(F.text == "👤 Hisobim")
async def hisobim(message: Message, bot: Bot):
    await db.update_last_active(message.from_user.id)
    user_id = message.from_user.id
    user = await db.get_user(user_id)
    if not user:
        return
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    total_refs, active_refs, inactive_refs = await db.get_referral_stats(user_id)
    await message.answer(
        f"👤 <b>Sizning hisobingiz:</b>\n\n"
        f"💸 Balans: <b>{user['balance']:,} so'm</b>\n"
        f"👥 Taklif qilganlar: <b>{total_refs} ta</b>\n"
        f"📈 Bugungi daromad: <b>{user['today_income']:,} so'm</b>\n"
        f"━━━━━━━━━━━\n"
        f"🔗 Sizning referal havolangiz:\n"
        f"<code>{ref_link}</code>\n"
        f"━━━━━━━━━━━\n"
        f"📊 Faol takliflar: <b>{active_refs} ta</b>\n"
        f"⚠️ Aktiv emas: <b>{inactive_refs} ta</b>\n"
        f"━━━━━━━━━━━\n"
        f"💡 Qancha ko'p aktiv odam — shuncha ko'p daromad!",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )


# ===================== TOP 10 =====================

@router.message(F.text == "🏆 TOP 10")
async def top10(message: Message):
    await db.update_last_active(message.from_user.id)
    top_users = await db.get_top10()
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    lines = ["🏆 <b>TOP 10 — Eng ko'p pul ishlagan foydalanuvchilar</b>\n"]
    for i, u in enumerate(top_users):
        lines.append(f"{medals[i]} {u['full_name']} — <b>{u['total_earned']:,} so'm</b>")
    if not top_users:
        lines.append("Hali hech kim yo'q 😊")
    await message.answer("\n".join(lines), reply_markup=back_keyboard(), parse_mode="HTML")


# ===================== PUL YECHISH =====================

@router.message(F.text == "💳 Pul yechish")
async def pul_yechish(message: Message, state: FSMContext):
    await db.update_last_active(message.from_user.id)
    user = await db.get_user(message.from_user.id)
    if not user:
        return
    min_withdraw = int(await db.get_setting("min_withdraw") or 5000)
    if user["balance"] < min_withdraw:
        await message.answer(
            f"❌ Balansingiz yetarli emas!\n\n"
            f"💸 Joriy balans: <b>{user['balance']:,} so'm</b>\n"
            f"📌 Minimal yechish: <b>{min_withdraw:,} so'm</b>",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )
        return

    methods = await db.get_payment_methods()
    if not methods:
        await message.answer("❌ To'lov usullari hali qo'shilmagan. Admin bilan bog'laning.")
        return

    await message.answer(
        f"💳 <b>To'lov usulini tanlang:</b>\n\n"
        f"💰 Balans: <b>{user['balance']:,} so'm</b>",
        reply_markup=payment_methods_keyboard(methods),
        parse_mode="HTML"
    )
    await state.set_state(WithdrawStates.choosing_method)


@router.message(WithdrawStates.choosing_method)
async def withdraw_choose_method(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        is_adm = await db.is_admin(message.from_user.id)
        await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard(is_adm))
        return

    methods = await db.get_payment_methods()
    method = next((m for m in methods if m["display_name"] == message.text), None)
    if not method:
        await message.answer("❌ Noto'g'ri tanlov. Ro'yxatdan tanlang.")
        return

    await state.update_data(method_name=method["name"], method_display=method["display_name"])
    min_withdraw = int(await db.get_setting("min_withdraw") or 5000)
    user = await db.get_user(message.from_user.id)
    await message.answer(
        f"✅ <b>{method['display_name']}</b> tanlandi.\n\n"
        f"💰 Balans: <b>{user['balance']:,} so'm</b>\n"
        f"📌 Minimal: <b>{min_withdraw:,} so'm</b>\n\n"
        f"💵 Qancha yechmoqchisiz?",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(WithdrawStates.waiting_amount)


@router.message(WithdrawStates.waiting_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        is_adm = await db.is_admin(message.from_user.id)
        await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard(is_adm))
        return
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
        return

    user = await db.get_user(message.from_user.id)
    min_withdraw = int(await db.get_setting("min_withdraw") or 5000)
    if amount < min_withdraw:
        await message.answer(f"❌ Minimal yechish: {min_withdraw:,} so'm")
        return
    if amount > user["balance"]:
        await message.answer(f"❌ Balansingiz yetarli emas! Balans: {user['balance']:,} so'm")
        return

    data = await state.get_data()
    await state.update_data(amount=amount)
    await message.answer(
        f"💳 <b>{data['method_display']}</b> raqamini kiriting\n"
        f"(karta yoki telefon raqami):",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(WithdrawStates.waiting_wallet)


@router.message(WithdrawStates.waiting_wallet)
async def withdraw_wallet(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        is_adm = await db.is_admin(message.from_user.id)
        await message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard(is_adm))
        return

    wallet = message.text.strip()
    data = await state.get_data()
    amount = data["amount"]
    method_name = data["method_name"]
    method_display = data["method_display"]
    user_id = message.from_user.id

    await db.update_balance(user_id, -amount, silent=True)
    await db.create_payment(user_id, amount, wallet, method_name)
    await state.clear()

    is_adm = await db.is_admin(user_id)
    await message.answer(
        f"✅ <b>So'rov qabul qilindi!</b>\n\n"
        f"💳 Usul: <b>{method_display}</b>\n"
        f"💰 Miqdor: <b>{amount:,} so'm</b>\n"
        f"🏦 Raqam: <code>{wallet}</code>\n\n"
        f"⏳ Admin ko'rib chiqadi va pul yuboriladi.",
        reply_markup=main_menu_keyboard(is_adm),
        parse_mode="HTML"
    )

    # To'lovlar kanaliga yuborish
    payment_channel = await db.get_setting("payment_channel")
    user = await db.get_user(user_id)
    uname = user["username"] or "yoq"
    channel_text = (
        f"💳 <b>Yangi pul yechish so'rovi</b>\n\n"
        f"👤 {user['full_name']} (@{uname})\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💳 Usul: <b>{method_display}</b>\n"
        f"💰 Miqdor: <b>{amount:,} so'm</b>\n"
        f"🏦 Raqam: <code>{wallet}</code>"
    )
    if payment_channel:
        try:
            await bot.send_message(payment_channel, channel_text, parse_mode="HTML")
        except Exception:
            pass

    # Adminlarga xabar
    admins = await db.get_admins()
    all_ids = list(ADMIN_IDS) + [a["user_id"] for a in admins]
    for admin_id in set(all_ids):
        try:
            await bot.send_message(admin_id, channel_text, parse_mode="HTML")
        except Exception:
            pass


# ===================== BONUS =====================

@router.message(F.text == "🎁 Bonus olish")
async def bonus_olish(message: Message):
    await db.update_last_active(message.from_user.id)
    user_id = message.from_user.id
    bonus_min = int(await db.get_setting("bonus_min") or 10)
    bonus_max = int(await db.get_setting("bonus_max") or 100)

    # Ko'pincha kam chiqsin — weighted random
    weights = list(range(bonus_max - bonus_min + 1, 0, -1))
    values = list(range(bonus_min, bonus_max + 1))
    amount = random.choices(values, weights=weights, k=1)[0]

    success = await db.claim_daily_bonus(user_id, amount)
    if success:
        await message.answer(
            f"🎁 <b>Kunlik bonus!</b>\n\n"
            f"🎉 Sizga <b>{amount} so'm</b> bonus berildi!\n\n"
            f"⏰ Ertaga yana keling!",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"⏳ Bugun allaqachon bonus oldingiz.\n\n"
            f"🔄 Ertaga yana keling!",
            reply_markup=back_keyboard(),
            parse_mode="HTML"
        )


# ===================== VAZIFALAR =====================

@router.message(F.text == "📋 Vazifalar")
async def vazifalar(message: Message):
    await db.update_last_active(message.from_user.id)
    user_id = message.from_user.id
    tasks = await db.get_active_tasks()
    if not tasks:
        await message.answer("📋 Hozircha vazifalar yo'q.", reply_markup=back_keyboard())
        return

    completed_ids = [t["id"] for t in tasks if await db.is_task_completed(user_id, t["id"])]
    await message.answer(
        f"📋 <b>Vazifalar</b>\n\n"
        f"✅ Bajarilgan: <b>{len(completed_ids)}/{len(tasks)}</b>\n\n"
        f"Vazifani tanlang:",
        reply_markup=tasks_list_keyboard(tasks, completed_ids),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("task:"))
async def task_callback(call: CallbackQuery, bot: Bot):
    await db.update_last_active(call.from_user.id)
    task_id = int(call.data.split(":")[1])
    user_id = call.from_user.id
    task = await db.get_task_by_id(task_id)
    if not task or not task["is_active"]:
        await call.answer("Bu vazifa topilmadi!", show_alert=True)
        return

    if await db.is_task_completed(user_id, task_id):
        await call.answer("Bu vazifani allaqachon bajargansiz!", show_alert=True)
        return

    # Kanal/guruh uchun obuna tekshirish
    if task["task_type"] in ("channel", "group") and task["link"]:
        ch_id = task["link"].strip()
        if not ch_id.startswith("-"):
            ch_id = "@" + ch_id.lstrip("@").lstrip("https://t.me/")
        try:
            member = await bot.get_chat_member(ch_id, user_id)
            if member.status in ["left", "kicked", "banned"]:
                await call.answer(
                    f"Avval obuna bo'ling: {task['link']}",
                    show_alert=True
                )
                return
        except Exception:
            pass

    success = await db.complete_task(user_id, task_id)
    if success:
        await db.update_balance(user_id, task["reward"])
        await call.answer(f"Vazifa bajarildi! +{task['reward']} so'm qo'shildi!", show_alert=True)
        tasks = await db.get_active_tasks()
        completed_ids = [t["id"] for t in tasks if await db.is_task_completed(user_id, t["id"])]
        try:
            await call.message.edit_reply_markup(reply_markup=tasks_list_keyboard(tasks, completed_ids))
        except Exception:
            pass
    else:
        await call.answer("Xatolik yuz berdi!", show_alert=True)


# ===================== TO'LOVLAR / ALOQA =====================

@router.message(F.text == "📢 To'lovlar")
async def tolovlar(message: Message):
    await db.update_last_active(message.from_user.id)
    channel = await db.get_setting("payment_channel") or "@foydauzb_tolov"
    await message.answer(
        f"📢 <b>To'lovlar kanali</b>\n\nBarcha to'lovlar:\n➡️ {channel}",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "📞 Aloqa")
async def aloqa(message: Message):
    await db.update_last_active(message.from_user.id)
    contact = await db.get_setting("contact_info") or "@admin"
    await message.answer(
        f"📞 <b>Aloqa</b>\n\nSavollar uchun:\n➡️ {contact}",
        reply_markup=back_keyboard(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔙 Orqaga")
async def orqaga(message: Message):
    await db.update_last_active(message.from_user.id)
    is_adm = await db.is_admin(message.from_user.id)
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu_keyboard(is_adm))
