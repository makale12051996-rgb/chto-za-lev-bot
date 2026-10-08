import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

WORK_START = 9
WORK_END = 21

bookings = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("✂️ Записаться", callback_data="booking")],
        [InlineKeyboardButton("💰 Прайс", callback_data="price")],
        [InlineKeyboardButton("📍 Адрес", callback_data="address")],
        [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
    ]

    await update.message.reply_text(
        "🦁 Добро пожаловать в барбершоп «Что за лев»!\n\n"
        "Здесь вы можете посмотреть прайс и записаться на удобное время.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_times(query):

    keyboard = []

    for hour in range(WORK_START, WORK_END):

        time_text = f"{hour:02d}:00"

        if time_text in bookings:
            keyboard.append([
                InlineKeyboardButton(
                    f"🔴 {time_text} — занято",
                    callback_data="busy"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    f"🟢 {time_text}",
                    callback_data=f"time_{time_text}"
                )
            ])

    keyboard.append([
        InlineKeyboardButton(
            "⬅️ Назад",
            callback_data="back"
        )
    ])

    await query.edit_message_text(
        "🦁 Выберите удобное время:\n\n"
        "⏰ Работаем с 09:00 до 21:00\n"
        "✂️ Продолжительность записи — 1 час",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "booking":

        await show_times(query)

    elif query.data == "price":

        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]

        await query.edit_message_text(
            "💰 ПРАЙС «ЧТО ЗА ЛЕВ»\n\n"
            "✂️ Обычная стрижка — 80 000 сум\n"
            "🪒 Под насадку — 50 000 сум\n"
            "💇 Удлинённая — 90 000–100 000 сум\n\n"
            "🧔 Бритьё бороды — 20 000 сум\n"
            "🧔 Моделирование бороды — 30 000–50 000 сум\n\n"
            "👦 Дети 6–12 лет — 60 000 сум\n"
            "👦 Дети 12–18 лет — 70 000 сум",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "address":

        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]

        await query.edit_message_text(
            "📍 НАШ АДРЕС\n\n"
            "Барбершоп «Что за лев» 🦁\n\n"
            "Здесь будет указан адрес барбершопа.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "contacts":

        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data="back")]
        ]

        await query.edit_message_text(
            "📞 КОНТАКТЫ\n\n"
            "Барбершоп «Что за лев» 🦁\n\n"
            "Для связи напишите нам в Telegram.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "back":

        keyboard = [
            [InlineKeyboardButton("✂️ Записаться", callback_data="booking")],
            [InlineKeyboardButton("💰 Прайс", callback_data="price")],
            [InlineKeyboardButton("📍 Адрес", callback_data="address")],
            [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
        ]

        await query.edit_message_text(
            "🦁 Барбершоп «Что за лев»\n\n"
            "Выберите нужный раздел:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "busy":

        await query.answer(
            "❌ Это время уже занято.",
            show_alert=True
        )

    elif query.data.startswith("time_"):

        time = query.data.replace("time_", "")

        if time in bookings:

            await query.answer(
                "❌ Это время уже занято.",
                show_alert=True
            )
            return

        bookings[time] = {
            "user_id": query.from_user.id,
            "name": query.from_user.full_name,
        }

        await query.edit_message_text(
            "✅ ЗАПИСЬ ПОДТВЕРЖДЕНА!\n\n"
            f"🕐 Время: {time}\n"
            f"👤 Клиент: {query.from_user.full_name}\n"
            "✂️ Барбершоп: «Что за лев»\n\n"
            "Ждём вас! 🦁\n"
            "Пожалуйста, приходите вовремя."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🦁 Я помогу вам записаться в барбершоп «Что за лев».\n\n"
        "Нажмите /start, чтобы открыть меню."
    )


def main():

    if not TOKEN:

        raise ValueError(
            "❌ BOT_TOKEN не найден!\n"
            "Добавьте BOT_TOKEN в Variables в Railway."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print("🦁 Бот «Что за лев» запущен!")

    app.run_polling()


if __name__ == "__main__":
    main()
