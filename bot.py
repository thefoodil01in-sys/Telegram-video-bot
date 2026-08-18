import os
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.environ.get("BOT_TOKEN")


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Apni script yahan bhejiye.\n"
        "Main script receive karke uski length bataunga."
    )


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return

    text = update.message.text
    length = len(text)

    await update.message.reply_text(
        "📝 Script mil gayi!\n\n"
        f"📊 Script length: {length} characters.\n\n"
        "🎬 Animation processing ke liye ready."
    )


def main():
    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN environment variable missing"
        )

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    app.add_handler(
        CommandHandler("start", start)
    )

    print("Animation bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
