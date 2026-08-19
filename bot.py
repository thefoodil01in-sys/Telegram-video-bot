import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
    level=logging.INFO
)

TOKEN = os.environ.get("BOT_TOKEN")


# Render Web Service ke liye simple HTTP server
class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Telegram bot is running!")

    def log_message(self, format, *args):
        return


def start_web_server():
    port = int(os.environ.get("PORT", 10000))

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"Web server running on port {port}")
    server.serve_forever()


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

    text = update.message.text.strip()

    if len(text) < 20:
        await update.message.reply_text(
            "⚠️ Script thodi badi bhejiye."
        )
        return

    length = len(text)

    await update.message.reply_text(
        "📄 Script mil gayi!\n\n"
        f"📝 Script length: {length} characters\n\n"
        "🎬 Animation banane ki taiyari ho rahi hai..."
    )

    try:
        with open("latest_script.txt", "w", encoding="utf-8") as f:
            f.write(text)

        await update.message.reply_text(
            "✅ Script successfully save ho gayi!\n\n"
            "🎬 Ab animation processing start hogi."
        )

    except Exception as e:
        await update.message.reply_text(
            f"❌ Script save nahi ho payi:\n{e}"
        )


def main():

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN environment variable missing"
        )

    # Render port server background me start karo
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )
    web_thread.start()

    # Telegram bot
    app = (
        Application.builder()
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

    print("Telegram bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
