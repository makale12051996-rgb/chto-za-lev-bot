
import os
import sqlite3
import logging
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7807661442

SHOP_NAME = "Что за лев"
SHOP_PHONE = "+998903345667"
SHOP_ADDRESS = (
    "Яшнабадский район, "
    "массив Городок Авиастроителей, "
    "4-й квартал, 5"
)

TIMEZONE = ZoneInfo("Asia/Tashkent")

WORK_START = 9
WORK_END = 21
DAYS_AHEAD = 7

DB_PATH = os.getenv("DB_PATH", "bookings.db")

BARBERS = {
    "h1": "Хабиб",
    "h2": "Хабиб младший",
    "h3": "Хусниддин",
}

PRICES = (
    "💰 ПРАЙС «ЧТО ЗА ЛЕВ»\n\n"
    "✂️ Стрижка под насадку — от 50 000 сум\n"
    "✂️ Обычная стрижка — 80 000 сум\n"
    "✂️ Удлинённая стрижка — 90 000–100 000 сум\n\n"
    "🧔 Бритьё бороды — 20 000 сум\n"
    "🧔 Моделирование бороды — 30 000–50 000 сум\n\n"
    "👦 Дети 6–12 лет — 60 000 сум\n"
    "👦 Подростки 12–18 лет — 70 000 сум"
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# =========================
# БАЗА ДАННЫХ
# =========================

def init_db():
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_date TEXT NOT NULL,
                barber_id TEXT NOT NULL,
                booking_time TEXT NOT NULL,
                client_name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (booking_date, barber_id, booking_time)
            )
        """)
        conn.commit()


def get_booked_times(booking_date, barber_id):
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        rows = conn.execute(
            """
            SELECT booking_time
            FROM bookings
            WHERE booking_date = ? AND barber_id = ?
            """,
            (booking_date, barber_id),
        ).fetchall()

    return {row[0] for row in rows}


def save_booking(
    booking_date,
    barber_id,
    booking_time,
    name,
    user_id,
):
    try:
        with sqlite3.connect(DB_PATH, timeout=30) as conn:
            conn.execute(
                """
                INSERT INTO bookings (
                    booking_date,
                    barber_id,
                    booking_time,
                    client_name,
                    user_id,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    booking_date,
                    barber_id,
                    booking_time,
                    name,
                    user_id,
                    datetime.now(TIMEZONE).isoformat(),
                ),
            )
            conn.commit()

        return True

    except sqlite3.IntegrityError:
        return False


# =========================
# КЛАВИАТУРЫ
# =========================

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✂️ Записаться",
                callback_data="booking",
            )
        ],
        [
            InlineKeyboardButton(
                "💰 Прайс",
                callback_data="price",
            )
        ],
        [
            InlineKeyboardButton(
                "📍 Адрес",
                callback_data="address",
            )
        ],
        [
            InlineKeyboardButton(
                "📞 Контакты",
                callback_data="contacts",
            )
        ],
    ])


def back_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔙 Назад",
                callback_data="back",
            )
        ]
    ])


def barber_keyboard():
    buttons = []

    for barber_id, barber_name in BARBERS.items():
        buttons.append([
            InlineKeyboardButton(
                f"💈 {barber_name}",
                callback_data=f"barber:{barber_id}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Назад",
            callback_data="back",
        )
    ])

    return InlineKeyboardMarkup(buttons)


def date_keyboard(barber_id):
    buttons = []
    today = datetime.now(TIMEZONE).date()

    for offset in range(DAYS_AHEAD):
        day = today + timedelta(days=offset)

        label = day.strftime("%d.%m.%Y")

        if offset == 0:
            label += " — сегодня"
        elif offset == 1:
            label += " — завтра"

        buttons.append([
            InlineKeyboardButton(
                label,
                callback_data=f"date:{barber_id}:{day.isoformat()}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Назад к мастерам",
            callback_data="booking",
        )
    ])

    return InlineKeyboardMarkup(buttons)


def get_available_times(booking_date, barber_id):
    selected_day = date.fromisoformat(booking_date)
    today = datetime.now(TIMEZONE).date()

    if not (
        today
        <= selected_day
        <= today + timedelta(days=DAYS_AHEAD - 1)
    ):
        return []

    booked = get_booked_times(booking_date, barber_id)
    available = []
    now = datetime.now(TIMEZONE)

    for hour in range(WORK_START, WORK_END):
        slot = time(hour, 0)
        slot_text = slot.strftime("%H:%M")

        if slot_text in booked:
            continue

        if selected_day == today:
            slot_datetime = datetime.combine(
                selected_day,
                slot,
                tzinfo=TIMEZONE,
            )

            if slot_datetime <= now:
                continue

        available.append(slot_text)

    return available


def time_keyboard(booking_date, barber_id):
    available = get_available_times(
        booking_date,
        barber_id,
    )

    buttons = []
    row = []

    for slot in available:
        row.append(
            InlineKeyboardButton(
                f"🕐 {slot}",
                callback_data=(
                    f"time:{barber_id}:{booking_date}:{slot}"
                ),
            )
        )

        if len(row) == 3:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    if not available:
        buttons.append([
            InlineKeyboardButton(
                "Нет свободного времени",
                callback_data="busy",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "📅 Выбрать другую дату",
            callback_data=f"barber:{barber_id}",
        )
    ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 Главное меню",
            callback_data="back",
        )
    ])

    return InlineKeyboardMarkup(buttons)


# =========================
# СТАРТОВОЕ МЕНЮ
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    text = (
        "🦁 Добро пожаловать в барбершоп "
        "«Что за лев»!\n\n"
        "Выберите нужный раздел:"
    )

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=main_keyboard(),
        )

    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=main_keyboard(),
        )


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await start(update, context)


# =========================
# ОБРАБОТКА КНОПОК
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    data = query.data or ""

    if data.startswith("time:"):
        parts = data.split(":")

        if len(parts) != 5:
            await query.answer(
                "Некорректное время.",
                show_alert=True,
            )
            return

        _, barber_id, booking_date, hour, minute = parts
        slot = f"{hour}:{minute}"

        if barber_id not in BARBERS:
            await query.answer(
                "Мастер не найден.",
                show_alert=True,
            )
            return

        try:
            selected_day = date.fromisoformat(booking_date)
            selected_time = datetime.strptime(
                slot, "%H:%M"
            ).time()
        except ValueError:
            await query.answer(
                "Некорректная дата или время.",
                show_alert=True,
            )
            return

        if slot not in get_available_times(
            booking_date, barber_id
        ):
            await query.answer(
                "Это время уже занято. Выберите другое.",
                show_alert=True,
            )
            await query.edit_message_reply_markup(
                reply_markup=time_keyboard(
                    booking_date, barber_id
                )
            )
            return

        await query.answer()

        context.user_data.clear()
        context.user_data["barber_id"] = barber_id
        context.user_data["booking_date"] = booking_date
        context.user_data["selected_time"] = slot
        context.user_data["waiting_name"] = True

        await query.edit_message_text(
            "🦁 Подтверждение записи\n\n"
            f"💈 Барбер: {BARBERS[barber_id]}\n"
            f"📅 Дата: {selected_day.strftime('%d.%m.%Y')}\n"
            f"🕐 Время: {selected_time.strftime('%H:%M')}\n\n"
            "Напишите ваше имя:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "❌ Отменить",
                        callback_data="back",
                    )
                ]
            ]),
        )
        return

    await query.answer()

    if data == "back":
        context.user_data.clear()

        await query.edit_message_text(
            "🦁 Барбершоп «Что за лев»\n\n"
            "Выберите нужный раздел:",
            reply_markup=main_keyboard(),
        )
        return

    if data == "booking":
        context.user_data.clear()

        await query.edit_message_text(
            "💈 Выберите своего барбера:",
            reply_markup=barber_keyboard(),
        )
        return

    if data.startswith("barber:"):
        barber_id = data.split(":", 1)[1]

        if barber_id not in BARBERS:
            await query.edit_message_text(
                "Мастер не найден. Начните запись заново.",
                reply_markup=main_keyboard(),
            )
            return

        context.user_data.clear()
        context.user_data["barber_id"] = barber_id

        await query.edit_message_text(
            f"💈 Мастер: {BARBERS[barber_id]}\n\n"
            "📅 Выберите дату записи:",
            reply_markup=date_keyboard(barber_id),
        )
        return

    if data.startswith("date:"):
        parts = data.split(":")

        if len(parts) != 3:
            return

        _, barber_id, booking_date = parts

        if barber_id not in BARBERS:
            return

        try:
            selected_day = date.fromisoformat(booking_date)
        except ValueError:
            await query.edit_message_text(
                "Некорректная дата. Начните запись заново.",
                reply_markup=main_keyboard(),
            )
            return

        today = datetime.now(TIMEZONE).date()

        if not (
            today
            <= selected_day
            <= today + timedelta(days=DAYS_AHEAD - 1)
        ):
            await query.edit_message_text(
                "Эта дата недоступна. Выберите другую.",
                reply_markup=date_keyboard(barber_id),
            )
            return

        context.user_data.clear()
        context.user_data["barber_id"] = barber_id
        context.user_data["booking_date"] = booking_date

        await query.edit_message_text(
            f"💈 Мастер: {BARBERS[barber_id]}\n"
            f"📅 Дата: {selected_day.strftime('%d.%m.%Y')}\n\n"
            "🕐 Выберите свободное время.\n"
            "Продолжительность — 1 час.",
            reply_markup=time_keyboard(
                booking_date, barber_id
            ),
        )
        return

    if data == "price":
        await query.edit_message_text(
            PRICES,
            reply_markup=back_keyboard(),
        )
        return

    if data == "address":
        await query.edit_message_text(
            f"📍 БАРБЕРШОП «{SHOP_NAME}»\n\n"
            f"Адрес: {SHOP_ADDRESS}\n\n"
            f"📱 Телефон: {SHOP_PHONE}",
            reply_markup=back_keyboard(),
        )
        return

    if data == "contacts":
        await query.edit_message_text(
            f"📞 КОНТАКТЫ\n\n"
            f"🦁 Барбершоп «{SHOP_NAME}»\n\n"
            f"Телефон: {SHOP_PHONE}\n\n"
            "Будем рады видеть вас!",
            reply_markup=back_keyboard(),
        )
        return

    if data == "busy":
        await query.answer(
            "Свободного времени нет. Выберите другую дату.",
            show_alert=True,
        )
        return


# =========================
# ПОЛУЧЕНИЕ ИМЕНИ И ЗАПИСЬ
# =========================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    if not context.user_data.get("waiting_name"):
        return

    if not update.message or not update.message.text:
        return

    name = update.message.text.strip()

    if not name:
        await update.message.reply_text(
            "Пожалуйста, напишите ваше имя."
        )
        return

    if len(name) > 80:
        await update.message.reply_text(
            "Имя слишком длинное. Напишите покороче."
        )
        return

    barber_id = context.user_data.get("barber_id")
    booking_date = context.user_data.get("booking_date")
    selected_time = context.user_data.get("selected_time")

    if (
        barber_id not in BARBERS
        or not booking_date
        or not selected_time
    ):
        context.user_data.clear()

        await update.message.reply_text(
            "Запись не найдена. Начните заново.",
            reply_markup=main_keyboard(),
        )
        return

    try:
        selected_day = date.fromisoformat(booking_date)
    except ValueError:
        context.user_data.clear()

        await update.message.reply_text(
            "Дата некорректна. Начните запись заново.",
            reply_markup=main_keyboard(),
        )
        return

    today = datetime.now(TIMEZONE).date()

    if not (
        today
        <= selected_day
        <= today + timedelta(days=DAYS_AHEAD - 1)
    ):
        context.user_data.clear()

        await update.message.reply_text(
            "Дата записи недоступна. Выберите заново.",
            reply_markup=main_keyboard(),
        )
        return

    if selected_time not in get_available_times(
        booking_date, barber_id
    ):
        context.user_data.clear()

        await update.message.reply_text(
            "❌ Это время уже заняли.\n\n"
            "Пожалуйста, выберите другое время.",
            reply_markup=main_keyboard(),
        )
        return

    user_id = update.effective_user.id

    saved = save_booking(
        booking_date,
        barber_id,
        selected_time,
        name,
        user_id,
    )

    if not saved:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ Это время только что заняли. "
            "Выберите другое.",
            reply_markup=main_keyboard(),
        )
        return

    context.user_data.clear()
    readable_date = selected_day.strftime("%d.%m.%Y")

    await update.message.reply_text(
        "✅ ЗАПИСЬ ПОДТВЕРЖДЕНА!\n\n"
        f"🦁 Барбершоп: «{SHOP_NAME}»\n"
        f"👤 Имя: {name}\n"
        f"💈 Барбер: {BARBERS[barber_id]}\n"
        f"📅 Дата: {readable_date}\n"
        f"🕐 Время: {selected_time}\n\n"
        "Пожалуйста, приходите вовремя.",
        reply_markup=main_keyboard(),
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "🔔 НОВАЯ ЗАПИСЬ!\n\n"
                f"🦁 Барбершоп: «{SHOP_NAME}»\n"
                f"👤 Клиент: {name}\n"
                f"💈 Барбер: {BARBERS[barber_id]}\n"
                f"📅 Дата: {readable_date}\n"
                f"🕐 Время: {selected_time}\n"
                f"🆔 Telegram ID: {user_id}"
            ),
        )
    except Exception:
        logger.exception(
            "Не удалось отправить уведомление владельцу"
        )


# =========================
# ЗАПУСК
# =========================

def main():
    if not TOKEN:
        raise ValueError(
            "Не найден BOT_TOKEN. "
            "Добавьте BOT_TOKEN в Variables на Railway."
        )

    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start_command)
    )

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    logger.info("Бот «Что за лев» запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()
            
