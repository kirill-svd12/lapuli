import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ApplicationBuilder, MessageHandler, filters, ConversationHandler
from telegram.error import Conflict
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

# Load environment variables
load_dotenv()

# Bot version
BOT_VERSION = "1.0.0"

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
WAITING_FOR_MESSAGE, WAITING_FOR_DATE, WAITING_FOR_TIME = range(3)

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

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Global variable for application
application = None

def get_back_button():
    """Return a back button for menus."""
    return [InlineKeyboardButton("◀️ Вернуться в меню", callback_data='back_to_menu')]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with buttons when the command /start is issued."""
    if update.effective_user.id in ADMIN_IDS:
        await admin_menu(update, context)
    else:
        keyboard = [
            [
                InlineKeyboardButton("Узнать свой ID", callback_data='get_id'),
                InlineKeyboardButton("Я админ", callback_data='check_admin')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f'Привет! Я бот для проверки администраторов (версия {BOT_VERSION}). Выберите действие:',
            reply_markup=reply_markup
        )

async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin menu with options."""
    keyboard = [
        [InlineKeyboardButton("Запланировать пост", callback_data='schedule_post')],
        [InlineKeyboardButton("Посмотреть расписание", callback_data='view_schedule')]
    ]
    
    # Добавляем кнопки плана только для Кирилла
    if update.effective_user.id == KIRILL_ID:
        keyboard.append([InlineKeyboardButton("Выполнение плана", callback_data='plan_status')])
    elif update.effective_user.id == MAX_ID:
        keyboard.append([InlineKeyboardButton("План", callback_data='view_plan')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if isinstance(update, CallbackQuery):
        await update.edit_message_text(
            "Меню администратора. Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Меню администратора. Выберите действие:",
            reply_markup=reply_markup
        )

async def schedule_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the process of scheduling a post."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("◀️ Вернуться в меню", callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Отправьте сообщение, которое нужно опубликовать:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_MESSAGE

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the message for scheduling."""
    context.user_data['post_message'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Опубликовать сейчас", callback_data='post_now')],
        [InlineKeyboardButton("Выбрать дату и время", callback_data='select_datetime')],
        get_back_button()[0]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите, когда опубликовать сообщение:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_DATE

async def select_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle datetime selection."""
    query = update.callback_query
    await query.answer()
    
    # Создаем клавиатуру с датами (сегодня и следующие 7 дней)
    keyboard = []
    today = datetime.now()
    for i in range(8):
        date = today + timedelta(days=i)
        date_str = date.strftime("%d.%m.%Y")
        keyboard.append([InlineKeyboardButton(date_str, callback_data=f'date_{date_str}')])
    
    keyboard.append(get_back_button())
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выберите дату публикации:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle time selection."""
    query = update.callback_query
    await query.answer()
    
    date_str = query.data.split('_')[1]
    context.user_data['selected_date'] = date_str
    
    # Создаем клавиатуру с временем (каждый час)
    keyboard = []
    for hour in range(24):
        time_str = f"{hour:02d}:00"
        keyboard.append([InlineKeyboardButton(time_str, callback_data=f'time_{time_str}')])
    
    keyboard.append(get_back_button())
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выберите время публикации:",
        reply_markup=reply_markup
    )
    return WAITING_FOR_TIME

async def schedule_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule the message for posting."""
    query = update.callback_query
    await query.answer()
    
    time_str = query.data.split('_')[1]
    date_str = context.user_data['selected_date']
    message = context.user_data['post_message']
    
    # Создаем datetime объект
    post_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    
    # Планируем отправку
    scheduler.add_job(
        send_scheduled_message,
        trigger=DateTrigger(run_date=post_time),
        args=[context.bot, message],
        id=f"post_{post_time.strftime('%Y%m%d%H%M')}"
    )
    
    keyboard = [get_back_button()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Сообщение запланировано на {date_str} в {time_str}",
        reply_markup=reply_markup
    )
    return ConversationHandler.END

async def send_scheduled_message(bot, message):
    """Send the scheduled message to the channel."""
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=message)
    except Exception as e:
        logging.error(f"Error sending scheduled message: {e}")

async def post_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Post the message to the channel."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'post_now':
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=context.user_data['post_message']
        )
        keyboard = [get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Сообщение опубликовано!",
            reply_markup=reply_markup
        )
    elif query.data == 'select_datetime':
        return await select_datetime(update, context)
    
    return ConversationHandler.END

async def view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the weekly schedule."""
    query = update.callback_query
    await query.answer()
    
    schedule_text = "Расписание:\n"
    for day, data in SCHEDULE.items():
        schedule_text += f"{day} - {data['author']}, {data['content']}\n"
    
    keyboard = [get_back_button()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        schedule_text,
        reply_markup=reply_markup
    )

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
    keyboard.append(get_back_button())
    
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
    
    keyboard = [get_back_button()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        plan_text,
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()

    if query.data == 'get_id':
        keyboard = [get_back_button()]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f'Ваш ID: {query.from_user.id}',
            reply_markup=reply_markup
        )
    
    elif query.data == 'check_admin':
        if query.from_user.id in ADMIN_IDS:
            await admin_menu(update, context)
        else:
            keyboard = [get_back_button()]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                'Вы не админ',
                reply_markup=reply_markup
            )
    
    elif query.data == 'back_to_menu':
        await admin_menu(update, context)
    
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
    
    elif query.data.startswith('date_'):
        return await select_time(update, context)
    
    elif query.data.startswith('time_'):
        return await schedule_message(update, context)
    
    elif query.data in ['post_now', 'select_datetime']:
        return await post_message(update, context)

async def shutdown(application: Application):
    """Shutdown the bot gracefully."""
    logging.info("Shutting down...")
    if scheduler.running:
        scheduler.shutdown()
    await application.stop()
    await application.shutdown()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logging.info(f"Received signal {signum}")
    if application:
        asyncio.create_task(shutdown(application))
    sys.exit(0)

def main():
    """Start the bot."""
    global application
    
    # Create the Application and pass it your bot's token
    TOKEN = os.getenv("BOT_TOKEN")
    application = ApplicationBuilder().token(TOKEN).build()

    # Start the scheduler
    scheduler.start()

    # Add handlers
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(schedule_post, pattern='^schedule_post$')],
        states={
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            WAITING_FOR_DATE: [CallbackQueryHandler(post_message, pattern='^(post_now|select_datetime)$')],
            WAITING_FOR_TIME: [
                CallbackQueryHandler(select_time, pattern='^date_'),
                CallbackQueryHandler(schedule_message, pattern='^time_')
            ]
        },
        fallbacks=[CommandHandler("start", start)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_callback))

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the Bot with error handling
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Conflict as e:
        logging.error(f"Conflict error: {e}")
        # Wait a bit and try to restart
        asyncio.sleep(5)
        main()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise

if __name__ == '__main__':
    main()
