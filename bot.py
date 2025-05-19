import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot version
BOT_VERSION = "1.0.0"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# List of jokes
JOKES = [
    "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 = Dec 25",
    "Как программист ломает голову? Он использует //",
    "Почему Python-разработчики носят очки? Потому что они не могут C#",
    "Что сказал программист, когда его спросили, как он находит ошибки в коде? 'Я просто читаю сообщения об ошибках'",
    "Почему JavaScript-разработчики носят очки? Потому что они не могут C#",
    "Как программист открывает банку? Он использует can opener",
    "Почему программисты всегда путают Хэллоуин и Рождество? Потому что Oct 31 = Dec 25",
    "Что сказал программист, когда его спросили, как он находит ошибки в коде? 'Я просто читаю сообщения об ошибках'",
    "Почему программисты путают Хэллоуин и Рождество? Потому что Oct 31 = Dec 25",
    "Как программист ломает голову? Он использует //"
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with buttons when the command /start is issued."""
    keyboard = [
        [
            InlineKeyboardButton("😄 Прочитать анекдот", callback_data='joke'),
            InlineKeyboardButton("ℹ️ Узнать версию", callback_data='version')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Привет! Я бот с анекдотами. Выберите действие:',
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()

    if query.data == 'joke':
        # Get a random joke from the list
        import random
        joke = random.choice(JOKES)
        keyboard = [
            [
                InlineKeyboardButton("😄 Ещё анекдот", callback_data='joke'),
                InlineKeyboardButton("ℹ️ Узнать версию", callback_data='version')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"{joke}\n\nХотите ещё?",
            reply_markup=reply_markup
        )
    
    elif query.data == 'version':
        keyboard = [
            [
                InlineKeyboardButton("😄 Прочитать анекдот", callback_data='joke'),
                InlineKeyboardButton("ℹ️ Узнать версию", callback_data='version')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text=f"Версия бота: {BOT_VERSION}",
            reply_markup=reply_markup
        )

async def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token
    TOKEN = "8054850906:AAEzFbH2FaeTjjQ7Z_kOlg8BOsV1iR--66o"
    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the Bot
    await application.initialize()
    await application.start()
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 
