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

# Временное хранение записей
# После перезапуска Railway записи сбросятся.
bookings = {}


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✂️ Записаться", callback_data="booking")],
        [InlineKeyboardButton("💰 Прайс", callback_data="price")],
        [InlineKeyboardButton("📍 Адрес", callback_data="address")],
        [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
    ]

    await update.message.reply_text(
        "🦁 Добро пожаловать в барбершоп «Что за лев»!\n\n"
        "Здесь можно быстро выбрать удобное время и записаться на стрижку.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# ПОКАЗ ВРЕМЕНИ
# =========================

async def show_times(query):
    keyboard = []

    for hour in range(WORK_START, WORK_END):
        time_text = f"{hour:02d}:00"

        if time_text in bookings:
            button_text = f"❌ {time_text} — занято"
            callback = "busy"
        else:
            button_text = f"🕐 {time_text}"
            callback = f"time_{time_text}"

        keyboard.append([
            InlineKeyboardButton(
                button_text,
                callback_data=callback
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data="back")
    ])

    await query.edit_message_text(
        "🕐 Выберите удобное время:\n\n"
        "Работаем с 09:00 до 21:00\n"
        "⏱ Продолжительность записи — 1 час",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# ОБРАБОТКА КНОПОК
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # Записаться
    if data == "booking":
        await show_times(query)
        return

    # Выбрано время
    if data.startswith("time_"):
        time = data.replace("time_", "")

        if time in bookings:
            await query.answer(
                "Это время уже занято.",
                show_alert=True
            )
            return

        context.user_data["selected_time"] = time

        await query.edit_message_text(
            f"🕐 Вы выбрали время: {time}\n\n"
            "Напишите ваше имя, чтобы подтвердить запись."
        )

        context.user_data["waiting_name"] = True
        return

    # Занятое время
    if data == "busy":
        await query.answer(
            "Это время уже занято. Выберите другое.",
            show_alert=True
        )
        return

    # Прайс
    if data == "price":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ]

        await query.edit_message_text(
            "💰 ПРАЙС «ЧТО ЗА ЛЕВ»\n\n"
            "✂️ Стрижка под насадку — от 50 000 сум\n"
            "✂️ Обычная стрижка — 80 000 сум\n"
            "✂️ Удлинённая стрижка — 90 000–100 000 сум\n\n"
            "🧔 Бритьё бороды — 20 000 сум\n"
            "🧔 Моделирование бороды — 30 000–50 000 сум\n\n"
            "👦 Дети 6–12 лет — 60 000 сум\n"
            "👦 Подростки 12–18 лет — 70 000 сум",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Адрес
    if data == "address":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ]

        await query.edit_message_text(
            "📍 БАРБЕРШОП «ЧТО ЗА ЛЕВ»\n\n"
            "Наш адрес:\n"
            "📌 Здесь укажи адрес своего барбершопа\n\n"
            "Если хочешь, я потом помогу добавить сюда "
            "кнопку с картой.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Контакты
    if data == "contacts":
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="back")]
        ]

        await query.edit_message_text(
            "📞 КОНТАКТЫ\n\n"
            "🦁 Барбершоп «Что за лев»\n\n"
            "Для связи и вопросов:\n"
            "📱 Здесь можно указать номер телефона\n\n"
            "Будем рады видеть вас!",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Назад
    if data == "back":
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


# =========================
# ПОЛУЧЕНИЕ ИМЕНИ
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_name"):
        return

    name = update.message.text.strip()
    time = context.user_data.get("selected_time")

    if not time:
        return

    # Проверяем, не заняли ли время пока клиент писал имя
    if time in bookings:
        context.user_data.clear()

        await update.message.reply_text(
            "❌ К сожалению, это время только что заняли.\n\n"
            "Пожалуйста, выберите другое время."
        )

        await start(update, context)
        return

    
    # Сохраняем запись
    bookings[time] = {
        "name": name,
        "user_id": update.effective_user.id,
    }

    context.user_data.clear()

    await update.message.reply_text(
        "ЗАПИСЬ ПОДТВЕРЖДЕНА!\n\n"
        f"Имя: {name}\n"
        f"Время: {time}\n"
        "Барбершоп: «Что за лев»\n\n"
        "Пожалуйста, приходите вовремя."
    )

    await context.bot.send_message(
        chat_id=7807661442,
        text=(
            "🔔 НОВАЯ ЗАПИСЬ!\n\n"
            f"Клиент: {name}\n"
            f"Время: {time}\n"
            "Барбершоп: «Что за лев»"
        )
    )
    
    
    
    

    

  

    
# =========================
# КОМАНДА /START
# =========================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# =========================
# ЗАПУСК БОТА
# =========================

def main():
    if not TOKEN:
        raise ValueError(
            "Не найден BOT_TOKEN. Добавьте BOT_TOKEN в Variables на Railway."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
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
