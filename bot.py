import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text

    await update.message.reply_text(
        "✅ Script mil gayi!\n\n"
        f"Script length: {len(text)} characters.\n\n"
        "Animation processing ke liye ready."
    )


def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable missing")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
