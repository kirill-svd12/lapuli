import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ApplicationBuilder, MessageHandler, filters, ConversationHandler

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
ADMIN_IDS = [
    6961912936,  # Макс
    5014279740,  # Кирилл
    456789123
]

MAX_ID = 6961912936
KIRILL_ID = 5014279740

# Channel ID for posting
CHANNEL_ID = "-1002339723141"  # Замените на ID вашего канала

# States for conversation
WAITING_FOR_MESSAGE, WAITING_FOR_DATE = range(2)

# Schedule dictionary
SCHEDULE = {
    "Понедельник": {"author": "МАКС", "content": "Советы новичкам"},
    "Вторник": {"author": "КИРИЛЛ", "content": "видео"},
    "Среда": {"author": "МАКС", "content": "рецензия"},
    "Четверг": {"author": "КИРИЛЛ", "content": "видео"},
    "Пятница": {"author": "МАКС", "content": "азбука"},
    "Суббота": {"author": "КИРИЛЛ", "content": "видео"},
    "Воскресенье": {"author": "МАКС, КИРИЛЛ", "content": "интервью"}
}

# Plan tracking
weekly_plan = {day: {"status": "❌", "author": data["author"], "content": data["content"]} 
               for day, data in SCHEDULE.items()}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with buttons when the command /start is issued."""
    keyboard = [
        [
            InlineKeyboardButton("Узнать свой ID", callback_data='get_id'),
            InlineKeyboardButton("Я админ", callback_data='check_admin')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Привет! Я бот для проверки администраторов. Выберите действие:',
        reply_markup=reply_markup
    )

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin menu with options."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Запланировать пост", callback_data='schedule_post')],
        [InlineKeyboardButton("Посмотреть расписание", callback_data='view_schedule')]
    ]
    
    # Добавляем кнопки плана только для Кирилла
    if query.from_user.id == KIRILL_ID:
        keyboard.append([InlineKeyboardButton("Выполнение плана", callback_data='plan_status')])
    elif query.from_user.id == MAX_ID:
        keyboard.append([InlineKeyboardButton("План", callback_data='view_plan')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Меню администратора. Выберите действие:",
        reply_markup=reply_markup
    )

async def schedule_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of scheduling a post."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Отправьте сообщение, которое нужно опубликовать:")
    return WAITING_FOR_MESSAGE

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the message for scheduling."""
    context.user_data['post_message'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Опубликовать сейчас", callback_data='post_now')],
        [InlineKeyboardButton("Выбрать дату и время", callback_data='select_datetime')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите, когда опубликовать сообщение:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_DATE

async def post_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post the message to the channel."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'post_now':
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=context.user_data['post_message']
        )
        await query.edit_message_text("Сообщение опубликовано!")
    else:
        # Здесь можно добавить логику для выбора даты и времени
        await query.edit_message_text("Функция выбора даты и времени будет добавлена позже")
    
    return ConversationHandler.END

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the weekly schedule."""
    query = update.callback_query
    await query.answer()
    
    schedule_text = "Расписание:\n"
    for day, data in SCHEDULE.items():
        schedule_text += f"{day} - {data['author']}, {data['content']}\n"
    
    await query.edit_message_text(schedule_text)

async def plan_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show and handle plan status for Kirill."""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for day, data in weekly_plan.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{day}: {data['author']} - {data['content']} {data['status']}",
                callback_data=f'toggle_{day}'
            )
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "Отметка выполнения плана:",
        reply_markup=reply_markup
    )

async def toggle_plan_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle plan status for a specific day."""
    query = update.callback_query
    await query.answer()
    
    day = query.data.split('_')[1]
    current_status = weekly_plan[day]["status"]
    new_status = "✅" if current_status == "❌" else "❌"
    weekly_plan[day]["status"] = new_status
    
    # Уведомляем Макса об изменении
    if day in SCHEDULE and "МАКС" in SCHEDULE[day]["author"]:
        await context.bot.send_message(
            chat_id=MAX_ID,
            text=f"Кирилл отметил выполнение плана на {day}: {new_status}"
        )
    
    # Обновляем отображение плана
    await plan_status(update, context)

async def view_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show plan status for Max."""
    query = update.callback_query
    await query.answer()
    
    plan_text = "Статус выполнения плана:\n"
    for day, data in weekly_plan.items():
        if "МАКС" in data["author"]:
            plan_text += f"{day}: {data['content']} {data['status']}\n"
    
    await query.edit_message_text(plan_text)

async def send_weekly_report():
    """Send weekly report to Max."""
    missed_posts = sum(1 for day, data in weekly_plan.items() 
                      if "МАКС" in data["author"] and data["status"] == "❌")
    
    report_text = f"Еженедельный отчет:\nПропущено постов: {missed_posts}"
    await context.bot.send_message(chat_id=MAX_ID, text=report_text)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()

    if query.data == 'get_id':
        await query.edit_message_text(f'Ваш ID: {query.from_user.id}')
    
    elif query.data == 'check_admin':
        if query.from_user.id in ADMIN_IDS:
            await admin_menu(update, context)
        else:
            await query.edit_message_text('Вы не админ')
    
    elif query.data == 'schedule_post':
        return await schedule_post(update, context)
    
    elif query.data == 'view_schedule':
        await view_schedule(update, context)
    
    elif query.data == 'plan_status':
        await plan_status(update, context)
    
    elif query.data == 'view_plan':
        await view_plan(update, context)
    
    elif query.data.startswith('toggle_'):
        await toggle_plan_status(update, context)
    
    elif query.data in ['post_now', 'select_datetime']:
        return await post_message(update, context)

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    TOKEN = os.getenv("BOT_TOKEN")
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(schedule_post, pattern='^schedule_post$')],
        states={
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            WAITING_FOR_DATE: [CallbackQueryHandler(post_message, pattern='^(post_now|select_datetime)$')]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
