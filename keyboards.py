from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ===================== USER =====================

def main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="💸 Pul ishlash"),
        KeyboardButton(text="💳 Pul yechish")
    )
    builder.row(
        KeyboardButton(text="👤 Hisobim"),
        KeyboardButton(text="🏆 TOP 10")
    )
    builder.row(
        KeyboardButton(text="🎁 Bonus olish"),
        KeyboardButton(text="📋 Vazifalar")
    )
    builder.row(
        KeyboardButton(text="📢 To'lovlar"),
        KeyboardButton(text="📞 Aloqa")
    )
    if is_admin:
        builder.row(KeyboardButton(text="🔐 Boshqaruv"))
    return builder.as_markup(resize_keyboard=True)


def back_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Orqaga")]],
        resize_keyboard=True
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )


def payment_methods_keyboard(methods: list) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    for m in methods:
        builder.row(KeyboardButton(text=m["display_name"]))
    builder.row(KeyboardButton(text="❌ Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)


def tasks_list_keyboard(tasks: list, completed_ids: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task in tasks:
        status = "✅" if task["id"] in completed_ids else "🔲"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {task['title']} (+{task['reward']} so'm)",
                callback_data=f"task:{task['id']}"
            )
        )
    return builder.as_markup()


def channels_sub_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(InlineKeyboardButton(text=f"📢 {ch['channel_name']}", url=ch["channel_link"]))
    builder.row(InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_subscription"))
    return builder.as_markup()


# ===================== ADMIN PANEL =====================

def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="⚙️ Asosiy sozlamalar"))
    builder.row(
        KeyboardButton(text="📊 Statistika"),
        KeyboardButton(text="📢 Xabar yuborish")
    )
    builder.row(KeyboardButton(text="👤 Foydalanuvchilar"))
    builder.row(
        KeyboardButton(text="💳 To'lovlar (pending)"),
        KeyboardButton(text="💰 Balans boshqarish")
    )
    builder.row(
        KeyboardButton(text="🎁 Bonus sozlash"),
        KeyboardButton(text="🏆 TOP sozlamalari")
    )
    builder.row(
        KeyboardButton(text="📋 Vazifalar qo'shish"),
        KeyboardButton(text="📢 Kanallar")
    )
    builder.row(
        KeyboardButton(text="💳 To'lov tizimlari"),
        KeyboardButton(text="📞 Aloqa sozlash")
    )
    builder.row(KeyboardButton(text="👥 Adminlar"))
    builder.row(KeyboardButton(text="🔙 Orqaga"))
    return builder.as_markup(resize_keyboard=True)


def users_management_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🔎 Qidirish (ID)"),
        KeyboardButton(text="🚫 Bloklash / Ban")
    )
    builder.row(KeyboardButton(text="🔙 Orqaga"))
    return builder.as_markup(resize_keyboard=True)


def payment_action_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_approve:{payment_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay_reject:{payment_id}")
    )
    return builder.as_markup()


def admin_channels_keyboard(channels: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        type_icon = "📢" if "channel" in ch["channel_type"] else ("👥" if "group" in ch["channel_type"] else "🔗")
        builder.row(
            InlineKeyboardButton(
                text=f"{type_icon} {ch['channel_name']}",
                callback_data=f"ch_info:{ch['id']}"
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"del_channel:{ch['id']}")
        )
    builder.row(InlineKeyboardButton(text="➕ Yangi qo'shish", callback_data="add_channel_menu"))
    return builder.as_markup()


def add_channel_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Kanal", callback_data="chtype:channel"))
    builder.row(InlineKeyboardButton(text="👥 Guruh", callback_data="chtype:group"))
    builder.row(InlineKeyboardButton(text="🔗 Havola", callback_data="chtype:link"))
    return builder.as_markup()


def add_channel_subtype_keyboard(parent: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Zayavka", callback_data=f"chsubtype:{parent}_request"))
    builder.row(InlineKeyboardButton(text="🔒 Shaxsiy", callback_data=f"chsubtype:{parent}_private"))
    builder.row(InlineKeyboardButton(text="🌐 Ommaviy", callback_data=f"chsubtype:{parent}_public"))
    return builder.as_markup()


def broadcast_type_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Oddiy xabar", callback_data="bcast:text"),
        InlineKeyboardButton(text="↩️ Forward xabar", callback_data="bcast:forward")
    )
    return builder.as_markup()


def admin_payment_methods_keyboard(methods: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for m in methods:
        status = "✅" if m["is_active"] else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {m['display_name']}",
                callback_data=f"toggle_pm:{m['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="➕ Yangi usul qo'shish", callback_data="add_pm"))
    return builder.as_markup()


def main_settings_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="1️⃣ Referal bonus"),
        KeyboardButton(text="2️⃣ Minimal yechish")
    )
    builder.row(
        KeyboardButton(text="3️⃣ Referal havola"),
        KeyboardButton(text="4️⃣ To'lovlar kanali")
    )
    builder.row(KeyboardButton(text="🔙 Orqaga"))
    return builder.as_markup(resize_keyboard=True)
