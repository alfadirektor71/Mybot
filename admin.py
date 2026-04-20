import re
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database as db
from keyboards import (
    admin_panel_keyboard, main_menu_keyboard, cancel_keyboard,
    users_management_keyboard, payment_action_keyboard,
    admin_channels_keyboard, add_channel_type_keyboard,
    add_channel_subtype_keyboard, broadcast_type_keyboard,
    admin_payment_methods_keyboard, main_settings_keyboard
)
from config import ADMIN_IDS

router = Router()
logger = logging.getLogger(__name__)


class AdminStates(StatesGroup):
    broadcast_text         = State()
    broadcast_forward_wait = State()
    search_uid             = State()
    ban_uid                = State()
    bal_uid                = State()
    bal_amount             = State()
    setting_value          = State()
    task_title             = State()
    task_desc              = State()
    task_reward            = State()
    task_link              = State()
    task_photo             = State()
    ch_name                = State()
    ch_forward_post        = State()
    ch_id_input            = State()
    ch_link_input          = State()
    pm_name                = State()
    pm_display             = State()
    new_admin_id           = State()


async def adm(uid: int) -> bool:
    return await db.is_admin(uid)


def parse_buttons(text: str):
    return re.findall(r"\[([^\[\]]+)\[([^\[\]]+)\]\]", text)


def build_inline_kb(buttons):
    if not buttons:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=n.strip(), url=u.strip())] for n, u in buttons]
    )


def strip_buttons(text: str) -> str:
    return re.sub(r"\[[^\[\]]+\[[^\[\]]+\]\]", "", text).strip()


@router.message(F.text == "🔐 Boshqaruv")
async def admin_panel(message: Message):
    if not await adm(message.from_user.id):
        return
    await message.answer(
        f"🔐 <b>Admin paneliga xush kelibsiz!</b>\n"
        f"🆔 Sizning ID: <code>{message.from_user.id}</code>",
        reply_markup=admin_panel_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    if not await adm(message.from_user.id):
        return
    s = await db.get_stats()
    await message.answer(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Jami: <b>{s['total_users']}</b>\n"
        f"✅ Aktiv: <b>{s['active_users']}</b>\n"
        f"━━━━━━━━━━━\n"
        f"🆕 24 soat: <b>{s['day1']}</b>\n"
        f"📅 30 kun: <b>{s['day30']}</b>\n"
        f"📅 60 kun: <b>{s['day60']}</b>\n"
        f"📅 90 kun: <b>{s['day90']}</b>\n"
        f"━━━━━━━━━━━\n"
        f"🟢 Ayni vaqtda aktiv: <b>{s['online_now']}</b>\n"
        f"━━━━━━━━━━━\n"
        f"⏳ Kutayotgan to'lovlar: <b>{s['pending_payments']}</b>\n"
        f"💰 Jami to'langan: <b>{s['total_paid']:,} so'm</b>",
        reply_markup=admin_panel_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "📢 Xabar yuborish")
async def broadcast_start(message: Message):
    if not await adm(message.from_user.id):
        return
    await message.answer("📢 <b>Xabar turini tanlang:</b>", reply_markup=broadcast_type_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "bcast:text")
async def bcast_text_start(call: CallbackQuery, state: FSMContext):
    if not await adm(call.from_user.id):
        return
    await call.message.answer(
        "✍️ Xabar matnini yuboring.\n\n📌 Tugma qo'shish:\n<code>[Nomi[https://havola.com]]</code>",
        reply_markup=cancel_keyboard(), parse_mode="HTML"
    )
    await state.set_state(AdminStates.broadcast_text)
    await call.answer()


@router.message(AdminStates.broadcast_text)
async def bcast_text_send(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    raw = message.html_text or message.text or ""
    buttons = parse_buttons(raw)
    clean_text = strip_buttons(raw)
    kb = build_inline_kb(buttons)
    users = await db.get_all_users()
    sent, failed = 0, 0
    for u in users:
        if u["is_banned"]:
            continue
        try:
            await bot.send_message(u["user_id"], clean_text, parse_mode="HTML", reply_markup=kb)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await message.answer(
        f"✅ Yuborildi!\n✅ Muvaffaqiyatli: <b>{sent}</b>\n❌ Yuborilmadi: <b>{failed}</b>",
        reply_markup=admin_panel_keyboard(), parse_mode="HTML"
    )


@router.callback_query(F.data == "bcast:forward")
async def bcast_forward_start(call: CallbackQuery, state: FSMContext):
    if not await adm(call.from_user.id):
        return
    await call.message.answer("↩️ Forward xabarni yuboring:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.broadcast_forward_wait)
    await call.answer()


@router.message(AdminStates.broadcast_forward_wait)
async def bcast_forward_send(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    users = await db.get_all_users()
    sent, failed = 0, 0
    for u in users:
        if u["is_banned"]:
            continue
        try:
            await bot.copy_message(chat_id=u["user_id"], from_chat_id=message.chat.id, message_id=message.message_id)
            sent += 1
        except Exception:
            failed += 1
    await state.clear()
    await message.answer(
        f"✅ Forward yuborildi!\n✅ Muvaffaqiyatli: <b>{sent}</b>\n❌ Yuborilmadi: <b>{failed}</b>",
        reply_markup=admin_panel_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "👤 Foydalanuvchilar")
async def users_menu(message: Message):
    if not await adm(message.from_user.id):
        return
    s = await db.get_stats()
    await message.answer(f"👤 <b>Foydalanuvchilar</b>\n\nJami: <b>{s['total_users']}</b>", reply_markup=users_management_keyboard(), parse_mode="HTML")


@router.message(F.text == "🔎 Qidirish (ID)")
async def search_start(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    await message.answer("🔎 Foydalanuvchi ID:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.search_uid)


@router.message(AdminStates.search_uid)
async def search_user(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!")
        return
    user = await db.get_user(uid)
    await state.clear()
    if not user:
        await message.answer("❌ Topilmadi.", reply_markup=users_management_keyboard())
        return
    status = "Bloklangan" if user["is_banned"] else "Aktiv"
    uname = user["username"] or "yoq"
    await message.answer(
        f"👤 <b>Foydalanuvchi</b>\n\nID: <code>{user['user_id']}</code>\nIsm: {user['full_name']}\n"
        f"Username: @{uname}\nBalans: <b>{user['balance']:,} so'm</b>\n"
        f"Referallar: <b>{user['referral_count']}</b>\nQo'shilgan: {str(user['joined_at'])[:10]}\nStatus: {status}",
        reply_markup=users_management_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "🚫 Bloklash / Ban")
async def ban_start(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    await message.answer("🚫 Foydalanuvchi ID:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.ban_uid)


@router.message(AdminStates.ban_uid)
async def ban_apply(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!")
        return
    user = await db.get_user(uid)
    await state.clear()
    if not user:
        await message.answer("❌ Topilmadi.", reply_markup=users_management_keyboard())
        return
    new_ban = not bool(user["is_banned"])
    await db.ban_user(uid, new_ban)
    action = "Bloklandi" if new_ban else "Blokdan chiqarildi"
    await message.answer(
        f"{'🚫' if new_ban else '✅'} {action}: <b>{user['full_name']}</b>",
        reply_markup=users_management_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "💳 To'lovlar (pending)")
async def pending_payments(message: Message):
    if not await adm(message.from_user.id):
        return
    payments = await db.get_pending_payments()
    if not payments:
        await message.answer("✅ Kutayotgan to'lov yo'q.", reply_markup=admin_panel_keyboard())
        return
    for p in payments:
        uname = p["username"] or "yoq"
        await message.answer(
            f"💳 <b>To'lov #{p['id']}</b>\n\n👤 {p['full_name']} (@{uname})\n"
            f"ID: <code>{p['user_id']}</code>\nUsul: <b>{p['payment_method']}</b>\n"
            f"Miqdor: <b>{p['amount']:,} so'm</b>\nRaqam: <code>{p['wallet_number']}</code>\n"
            f"Sana: {str(p['created_at'])[:16]}",
            reply_markup=payment_action_keyboard(p["id"]), parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("pay_approve:"))
async def approve_payment(call: CallbackQuery, bot: Bot):
    if not await adm(call.from_user.id):
        return
    pid = int(call.data.split(":")[1])
    payment = await db.get_payment_by_id(pid)
    if not payment or payment["status"] != "pending":
        await call.answer("Allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    await db.update_payment_status(pid, "approved")
    try:
        await call.message.edit_text(call.message.text + "\n\n✅ <b>TASDIQLANDI</b>", parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(
            payment["user_id"],
            f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\nUsul: <b>{payment['payment_method']}</b>\n"
            f"Miqdor: <b>{payment['amount']:,} so'm</b>\nRaqam: <code>{payment['wallet_number']}</code>\n\nPul tez orada tushadi!",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer("✅ Tasdiqlandi!")


@router.callback_query(F.data.startswith("pay_reject:"))
async def reject_payment(call: CallbackQuery, bot: Bot):
    if not await adm(call.from_user.id):
        return
    pid = int(call.data.split(":")[1])
    payment = await db.get_payment_by_id(pid)
    if not payment or payment["status"] != "pending":
        await call.answer("Allaqachon ko'rib chiqilgan!", show_alert=True)
        return
    await db.update_payment_status(pid, "rejected")
    await db.update_balance(payment["user_id"], payment["amount"])
    try:
        await call.message.edit_text(call.message.text + "\n\n❌ <b>RAD ETILDI</b>", parse_mode="HTML")
    except Exception:
        pass
    try:
        await bot.send_message(
            payment["user_id"],
            f"❌ <b>To'lov rad etildi.</b>\n\n<b>{payment['amount']:,} so'm</b> balansingizga qaytarildi.",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer("❌ Rad etildi!")


@router.message(F.text == "💰 Balans boshqarish")
async def bal_start(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    await message.answer("💰 Foydalanuvchi ID:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.bal_uid)


@router.message(AdminStates.bal_uid)
async def bal_get_uid(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!")
        return
    user = await db.get_user(uid)
    if not user:
        await message.answer("❌ Topilmadi.")
        return
    await state.update_data(target_uid=uid)
    await message.answer(
        f"👤 {user['full_name']}\nBalans: <b>{user['balance']:,} so'm</b>\n\n"
        f"Miqdor kiriting:\nQo'shish: <code>500</code>  Ayirish: <code>-200</code>",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.bal_amount)


@router.message(AdminStates.bal_amount)
async def bal_apply(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Raqam kiriting!")
        return
    data = await state.get_data()
    uid = data["target_uid"]
    await db.admin_update_balance(uid, amount)
    await state.clear()
    sign = "+" if amount > 0 else ""
    await message.answer(
        f"✅ Balans yangilandi!\nUser: <code>{uid}</code>\nO'zgarish: <b>{sign}{amount:,} so'm</b>",
        reply_markup=admin_panel_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "⚙️ Asosiy sozlamalar")
async def main_settings_menu(message: Message):
    if not await adm(message.from_user.id):
        return
    ref_bonus = await db.get_setting("referral_bonus") or "180"
    min_w     = await db.get_setting("min_withdraw")    or "5000"
    pay_ch    = await db.get_setting("payment_channel") or "@foydauzb_tolov"
    await message.answer(
        f"⚙️ <b>Asosiy sozlamalar</b>\n\n"
        f"1️⃣ Referal bonus: <b>{ref_bonus} so'm</b>\n"
        f"2️⃣ Minimal yechish: <b>{min_w} so'm</b>\n"
        f"3️⃣ To'lovlar kanali: <b>{pay_ch}</b>",
        reply_markup=main_settings_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "1️⃣ Referal bonus")
async def set_ref_bonus(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    cur = await db.get_setting("referral_bonus") or "180"
    await message.answer(f"Hozirgi: <b>{cur} so'm</b>\nYangi miqdorni kiriting:", reply_markup=cancel_keyboard(), parse_mode="HTML")
    await state.update_data(skey="referral_bonus")
    await state.set_state(AdminStates.setting_value)


@router.message(F.text == "2️⃣ Minimal yechish")
async def set_min_withdraw(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    cur = await db.get_setting("min_withdraw") or "5000"
    await message.answer(f"Hozirgi: <b>{cur} so'm</b>\nYangi miqdorni kiriting:", reply_markup=cancel_keyboard(), parse_mode="HTML")
    await state.update_data(skey="min_withdraw")
    await state.set_state(AdminStates.setting_value)


@router.message(F.text == "3️⃣ To'lovlar kanali")
async def set_pay_channel(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    cur = await db.get_setting("payment_channel") or "@foydauzb_tolov"
    await message.answer(f"Hozirgi: <b>{cur}</b>\nYangi kanal:", reply_markup=cancel_keyboard(), parse_mode="HTML")
    await state.update_data(skey="payment_channel")
    await state.set_state(AdminStates.setting_value)


@router.message(AdminStates.setting_value)
async def save_setting_val(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    data = await state.get_data()
    key = data.get("skey", "")
    if key == "bonus_range":
        parts = message.text.strip().split()
        if len(parts) == 2:
            try:
                bmin, bmax = int(parts[0]), int(parts[1])
                if bmin < 1 or bmin >= bmax:
                    raise ValueError
                await db.set_setting("bonus_min", str(bmin))
                await db.set_setting("bonus_max", str(bmax))
                await state.clear()
                await message.answer(f"✅ Bonus: <b>{bmin} — {bmax} so'm</b>", reply_markup=admin_panel_keyboard(), parse_mode="HTML")
                return
            except ValueError:
                await message.answer("❌ Misol: <code>5 80</code>", parse_mode="HTML")
                return
        await message.answer("❌ Misol: <code>5 80</code>", parse_mode="HTML")
        return
    await db.set_setting(key, message.text.strip())
    await state.clear()
    await message.answer(f"✅ Saqlandi: <code>{message.text.strip()}</code>", reply_markup=admin_panel_keyboard(), parse_mode="HTML")


@router.message(F.text == "🎁 Bonus sozlash")
async def bonus_settings(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    bmin = await db.get_setting("bonus_min") or "10"
    bmax = await db.get_setting("bonus_max") or "100"
    await message.answer(
        f"🎁 <b>Kunlik bonus</b>\n\nMin: <b>{bmin} so'm</b>  Max: <b>{bmax} so'm</b>\n\nYangi qiymat:\nMisol: <code>5 80</code>",
        reply_markup=cancel_keyboard(), parse_mode="HTML"
    )
    await state.update_data(skey="bonus_range")
    await state.set_state(AdminStates.setting_value)


@router.message(F.text == "💳 To'lov tizimlari")
async def payment_systems(message: Message):
    if not await adm(message.from_user.id):
        return
    methods = await db.get_all_payment_methods()
    await message.answer("💳 <b>To'lov tizimlari</b>\n\n✅ yoqilgan  ❌ o'chirilgan\nBosing:", reply_markup=admin_payment_methods_keyboard(methods), parse_mode="HTML")


@router.callback_query(F.data.startswith("toggle_pm:"))
async def toggle_pm(call: CallbackQuery):
    if not await adm(call.from_user.id):
        return
    mid = int(call.data.split(":")[1])
    methods = await db.get_all_payment_methods()
    method = next((m for m in methods if m["id"] == mid), None)
    if not method:
        await call.answer("Topilmadi!")
        return
    await db.toggle_payment_method(mid, not bool(method["is_active"]))
    methods = await db.get_all_payment_methods()
    try:
        await call.message.edit_reply_markup(reply_markup=admin_payment_methods_keyboard(methods))
    except Exception:
        pass
    await call.answer("✅ Yangilandi!")


@router.callback_query(F.data == "add_pm")
async def add_pm_start(call: CallbackQuery, state: FSMContext):
    if not await adm(call.from_user.id):
        return
    await call.message.answer("Yangi to'lov usuli ichki nomi (misol: <code>click</code>):", reply_markup=cancel_keyboard(), parse_mode="HTML")
    await state.set_state(AdminStates.pm_name)
    await call.answer()


@router.message(AdminStates.pm_name)
async def pm_get_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    await state.update_data(pm_name=message.text.strip().lower())
    await message.answer("Ko'rsatiladigan nom (misol: <code>Click</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.pm_display)


@router.message(AdminStates.pm_display)
async def pm_get_display(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    data = await state.get_data()
    await db.add_payment_method(data["pm_name"], message.text.strip())
    await state.clear()
    await message.answer(f"✅ Qo'shildi: <b>{message.text.strip()}</b>", reply_markup=admin_panel_keyboard(), parse_mode="HTML")


@router.message(F.text == "🏆 TOP sozlamalari")
async def top_view(message: Message):
    if not await adm(message.from_user.id):
        return
    top = await db.get_top10()
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines = ["🏆 <b>Joriy TOP 10</b>\n"]
    for i, u in enumerate(top):
        lines.append(f"{medals[i]} {u['full_name']} — {u['total_earned']:,} so'm")
    if not top:
        lines.append("Hali hech kim yo'q")
    await message.answer("\n".join(lines), reply_markup=admin_panel_keyboard(), parse_mode="HTML")


@router.message(F.text == "📋 Vazifalar qo'shish")
async def add_task_menu(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    tasks = await db.get_active_tasks()
    task_list = "\n".join([f"• #{t['id']} {t['title']} (+{t['reward']} so'm)" for t in tasks]) or "Hali yo'q"
    await message.answer(f"📋 <b>Mavjud vazifalar:</b>\n{task_list}\n\n➕ Yangi vazifa nomini kiriting:", reply_markup=cancel_keyboard(), parse_mode="HTML")
    await state.set_state(AdminStates.task_title)


@router.message(AdminStates.task_title)
async def get_task_title(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    await state.update_data(task_title=message.text.strip())
    await message.answer("📝 Tavsif (kerak bo'lmasa <code>skip</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.task_desc)


@router.message(AdminStates.task_desc)
async def get_task_desc(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    desc = "" if message.text.strip().lower() == "skip" else message.text.strip()
    await state.update_data(task_desc=desc)
    await message.answer("💰 Mukofot miqdori (so'm):")
    await state.set_state(AdminStates.task_reward)


@router.message(AdminStates.task_reward)
async def get_task_reward(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    try:
        reward = int(message.text.strip())
        if reward <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Musbat raqam kiriting!")
        return
    await state.update_data(task_reward=reward)
    await message.answer("🔗 Kanal @username yoki link (kerak bo'lmasa <code>skip</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.task_link)


@router.message(AdminStates.task_link)
async def get_task_link(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    link = "" if message.text.strip().lower() == "skip" else message.text.strip()
    await state.update_data(task_link=link)
    await message.answer("🖼 Rasm yuboring (kerak bo'lmasa <code>skip</code>):", parse_mode="HTML")
    await state.set_state(AdminStates.task_photo)


@router.message(AdminStates.task_photo)
async def get_task_photo(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    photo_id = None
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip().lower() == "skip":
        photo_id = None
    else:
        await message.answer("❌ Rasm yuboring yoki <code>skip</code>:", parse_mode="HTML")
        return
    data = await state.get_data()
    await state.clear()
    link = data.get("task_link", "")
    if link and ("t.me" in link or link.startswith("@")):
        task_type = "channel"
    elif link:
        task_type = "link"
    else:
        task_type = "none"
    await db.add_task(title=data["task_title"], description=data["task_desc"], reward=data["task_reward"], link=link, task_type=task_type, photo_id=photo_id)
    await message.answer(
        f"✅ <b>Vazifa qo'shildi!</b>\n\nNomi: {data['task_title']}\nMukofot: {data['task_reward']:,} so'm\nLink: {link or 'yoq'}",
        reply_markup=admin_panel_keyboard(), parse_mode="HTML"
    )


@router.message(F.text == "📢 Kanallar")
async def channels_menu(message: Message):
    if not await adm(message.from_user.id):
        return
    channels = await db.get_active_channels()
    await message.answer(f"📢 <b>Majburiy obuna kanallar</b>\nJami: <b>{len(channels)}</b> ta", reply_markup=admin_channels_keyboard(channels), parse_mode="HTML")


@router.callback_query(F.data == "add_channel_menu")
async def add_ch_menu(call: CallbackQuery):
    if not await adm(call.from_user.id):
        return
    await call.message.answer("➕ <b>Qo'shish turini tanlang:</b>", reply_markup=add_channel_type_keyboard(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("chtype:"))
async def chtype_select(call: CallbackQuery, state: FSMContext):
    if not await adm(call.from_user.id):
        return
    parent = call.data.split(":")[1]
    if parent == "link":
        await state.update_data(ch_type="link")
        await call.message.answer("🔗 Havola nomini kiriting:", reply_markup=cancel_keyboard())
        await state.set_state(AdminStates.ch_name)
        await call.answer()
        return
    await call.message.answer(
        f"{'📢 Kanal' if parent == 'channel' else '👥 Guruh'} turini tanlang:",
        reply_markup=add_channel_subtype_keyboard(parent)
    )
    await call.answer()


@router.callback_query(F.data.startswith("chsubtype:"))
async def chsubtype_select(call: CallbackQuery, state: FSMContext):
    if not await adm(call.from_user.id):
        return
    ch_type = call.data.split(":")[1]
    await state.update_data(ch_type=ch_type)
    if ch_type.endswith("_request"):
        await call.message.answer(
            "📢 <b>So'rovli kanal qo'shish</b>\n\n"
            "1. Botni kanalga admin qiling\n"
            "2. Kanaldan istalgan postni <b>forward</b> qiling:",
            reply_markup=cancel_keyboard(), parse_mode="HTML"
        )
        await state.set_state(AdminStates.ch_forward_post)
    else:
        await call.message.answer("📝 Kanal/guruh nomini kiriting:", reply_markup=cancel_keyboard())
        await state.set_state(AdminStates.ch_name)
    await call.answer()


@router.message(AdminStates.ch_forward_post)
async def ch_get_forward_post(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    if message.forward_from_chat:
        ch_id = str(message.forward_from_chat.id)
        ch_name = message.forward_from_chat.title or "Kanal"
        await state.update_data(ch_id=ch_id, ch_name=ch_name)
        await message.answer(
            f"✅ Kanal topildi: <b>{ch_name}</b>\nID: <code>{ch_id}</code>\n\n"
            f"🔗 Zayavka havolasini kiriting (https://t.me/+...):",
            reply_markup=cancel_keyboard(), parse_mode="HTML"
        )
        await state.set_state(AdminStates.ch_link_input)
    else:
        await message.answer("❌ Bu forward xabar emas!\n\nKanaldan postni <b>forward</b> qiling:", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(AdminStates.ch_name)
async def ch_get_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    await state.update_data(ch_name=message.text.strip())
    data = await state.get_data()
    ch_type = data.get("ch_type", "channel_public")
    if ch_type == "link":
        await message.answer("🔗 Havolani kiriting (https://...):")
        await state.set_state(AdminStates.ch_link_input)
    elif ch_type.endswith("_public"):
        await message.answer("📢 @username kiriting (bot admin bo'lishi kerak):")
        await state.set_state(AdminStates.ch_id_input)
    else:
        await message.answer("🔒 Kanal/guruh ID kiriting (-100... formatida):")
        await state.set_state(AdminStates.ch_id_input)


@router.message(AdminStates.ch_id_input)
async def ch_get_id(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    await state.update_data(ch_id=message.text.strip())
    await message.answer("🔗 Kanal/guruh havolasini kiriting (https://t.me/...):")
    await state.set_state(AdminStates.ch_link_input)


@router.message(AdminStates.ch_link_input)
async def ch_get_link(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    data = await state.get_data()
    ch_type = data.get("ch_type", "channel_public")
    ch_name = data.get("ch_name", "")
    ch_link = message.text.strip()
    ch_id = data.get("ch_id", ch_link)
    await state.clear()
    await db.add_channel(ch_id, ch_name, ch_link, ch_type)
    channels = await db.get_active_channels()
    await message.answer(f"✅ Qo'shildi: <b>{ch_name}</b>", reply_markup=admin_channels_keyboard(channels), parse_mode="HTML")


@router.callback_query(F.data.startswith("ch_info:"))
async def ch_info(call: CallbackQuery):
    if not await adm(call.from_user.id):
        return
    ch_db_id = int(call.data.split(":")[1])
    channels = await db.get_active_channels()
    ch = next((c for c in channels if c["id"] == ch_db_id), None)
    if not ch:
        await call.answer("Topilmadi!", show_alert=True)
        return
    import aiosqlite
    from database import DB_PATH
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute(
            "SELECT COUNT(*) FROM join_requests WHERE channel_id=?",
            (str(ch["channel_id"]),)
        ) as cur:
            count = (await cur.fetchone())[0]
    type_names = {
        "channel_public": "Ommaviy kanal",
        "channel_private": "Shaxsiy kanal",
        "channel_request": "Zayavkali kanal",
        "group_public": "Ommaviy guruh",
        "group_private": "Shaxsiy guruh",
        "group_request": "Zayavkali guruh",
        "link": "Havola"
    }
    ch_type = type_names.get(ch["channel_type"], ch["channel_type"])
    from keyboards import channel_info_keyboard
    text = (
        "<b>" + ch["channel_name"] + "</b>\n\n"
        + "ID: <code>" + str(ch["channel_id"]) + "</code>\n"
        + "Havola: " + ch["channel_link"] + "\n"
        + "Turi: " + ch_type + "\n"
        + "Zayavkalar: <b>" + str(count) + " ta</b>"
    )
    await call.message.edit_text(
        text,
        reply_markup=channel_info_keyboard(ch_db_id),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "back_to_channels")
async def back_to_channels(call: CallbackQuery):
    if not await adm(call.from_user.id):
        return
    channels = await db.get_active_channels()
    from keyboards import admin_channels_keyboard
    await call.message.edit_text(
        "Majburiy obuna kanallar\nJami: <b>" + str(len(channels)) + "</b> ta",
        reply_markup=admin_channels_keyboard(channels),
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data.startswith("del_channel:"))
async def del_channel(call: CallbackQuery):
    if not await adm(call.from_user.id):
        return
    ch_db_id = int(call.data.split(":")[1])
    await db.remove_channel(ch_db_id)
    channels = await db.get_active_channels()
    try:
        await call.message.edit_reply_markup(reply_markup=admin_channels_keyboard(channels))
    except Exception:
        pass
    await call.answer("✅ O'chirildi!")


@router.message(F.text == "📞 Aloqa sozlash")
async def contact_settings(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    cur = await db.get_setting("contact_info") or "@admin"
    await message.answer(f"📞 Hozirgi: <b>{cur}</b>\n\nYangi aloqa:", reply_markup=cancel_keyboard(), parse_mode="HTML")
    await state.update_data(skey="contact_info")
    await state.set_state(AdminStates.setting_value)


@router.message(F.text == "👥 Adminlar")
async def admins_list(message: Message):
    if not await adm(message.from_user.id):
        return
    admins = await db.get_admins()
    lines = ["👥 <b>Adminlar</b>\n"]
    if admins:
        for a in admins:
            lines.append(f"• {a['full_name']} — <code>{a['user_id']}</code>")
    else:
        lines.append("(qo'shimcha admin yo'q)")
    lines.append("\n<b>Asosiy adminlar:</b>")
    for aid in ADMIN_IDS:
        lines.append(f"• <code>{aid}</code>")
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Admin qo'shish"), KeyboardButton(text="➖ Admin o'chirish")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )
    await message.answer("\n".join(lines), reply_markup=kb, parse_mode="HTML")


@router.message(F.text == "➕ Admin qo'shish")
async def add_admin_start(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    await message.answer("🆔 Yangi admin Telegram ID:", reply_markup=cancel_keyboard())
    await state.update_data(admin_action="add")
    await state.set_state(AdminStates.new_admin_id)


@router.message(F.text == "➖ Admin o'chirish")
async def remove_admin_start(message: Message, state: FSMContext):
    if not await adm(message.from_user.id):
        return
    await message.answer("🆔 O'chirilayotgan admin ID:", reply_markup=cancel_keyboard())
    await state.update_data(admin_action="remove")
    await state.set_state(AdminStates.new_admin_id)


@router.message(AdminStates.new_admin_id)
async def admin_action_handler(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor.", reply_markup=admin_panel_keyboard())
        return
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam!")
        return
    data = await state.get_data()
    action = data.get("admin_action", "add")
    await state.clear()
    if action == "add":
        user = await db.get_user(uid)
        name = user["full_name"] if user else f"User {uid}"
        await db.add_admin(uid, name)
        await message.answer(f"✅ Admin qo'shildi: <b>{name}</b> (<code>{uid}</code>)", reply_markup=admin_panel_keyboard(), parse_mode="HTML")
        try:
            await bot.send_message(uid, "Siz admin qildingiz! /start bosing.")
        except Exception:
            pass
    else:
        await db.remove_admin(uid)
        await message.answer(f"✅ Admin o'chirildi: <code>{uid}</code>", reply_markup=admin_panel_keyboard(), parse_mode="HTML")


@router.message(F.text == "🔙 Orqaga")
async def back_to_main(message: Message):
    is_adm = await db.is_admin(message.from_user.id)
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu_keyboard(is_adm))
