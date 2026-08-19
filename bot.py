import os
import logging
import threading
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import replicate

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
REPLICATE_TOKEN = os.environ.get("REPLICATE_API_TOKEN")

MODEL = "prunaai/p-video"


# -----------------------------
# Render health-check server
# -----------------------------

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


# -----------------------------
# /start
# -----------------------------

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data.clear()

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "🖼️ Pehle ek image bhejiye.\n"
        "Uske baad main animation prompt maangunga.\n\n"
        "🎬 Example:\n"
        "Slowly move the camera forward. "
        "Keep the characters and background consistent."
    )


# -----------------------------
# IMAGE RECEIVED
# -----------------------------

async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.photo:
        return

    try:

        photo = update.message.photo[-1]

        telegram_file = await context.bot.get_file(
            photo.file_id
        )

        image_path = f"/tmp/{update.effective_user.id}_source.jpg"

        await telegram_file.download_to_drive(
            image_path
        )

        context.user_data["image_path"] = image_path

        await update.message.reply_text(
            "🖼️ Image mil gayi! ✅\n\n"
            "Ab animation ka **motion prompt** bhejiye.\n\n"
            "Example:\n"
            "Slowly push the camera forward. "
            "Keep the characters, faces, clothing, "
            "lighting and background consistent. "
            "Natural subtle movement only."
        )

    except Exception as e:

        logging.exception("Image download failed")

        await update.message.reply_text(
            f"❌ Image save nahi ho payi.\n\n{e}"
        )


# -----------------------------
# GENERATE VIDEO
# -----------------------------

def generate_video(
    image_path,
    prompt
):

    with open(image_path, "rb") as image_file:

        output = replicate.run(
            MODEL,
            input={
                "image": image_file,
                "prompt": prompt,
                "duration": 5,
                "resolution": "720p",
                "fps": 24,
                "prompt_upsampling": True,
                "save_audio": False,
            }
        )

    return output


# -----------------------------
# TEXT / PROMPT RECEIVED
# -----------------------------

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Image abhi nahi mili
    image_path = context.user_data.get("image_path")

    if not image_path:

        await update.message.reply_text(
            "🖼️ Pehle image bhejiye.\n\n"
            "Uske baad animation prompt bhejna."
        )

        return

    if len(text) < 10:

        await update.message.reply_text(
            "⚠️ Motion prompt thoda detailed bhejiye."
        )

        return

    await update.message.reply_text(
        "🎬 Animation processing START ho gayi!\n\n"
        "⏳ AI image ko video mein convert kar raha hai...\n"
        "Please wait."
    )

    try:

        # Blocking Replicate call ko background thread mein run karo
        output = await asyncio.to_thread(
            generate_video,
            image_path,
            text
        )

        video_path = (
            f"/tmp/{update.effective_user.id}_animation.mp4"
        )

        # Current Replicate Python client FileOutput
        with open(video_path, "wb") as video_file:

            if hasattr(output, "read"):
                video_file.write(output.read())

            elif isinstance(output, (list, tuple)):
                video_file.write(output[0].read())

            else:
                raise RuntimeError(
                    "Unexpected video output received."
                )

        await update.message.reply_text(
            "✅ Animation successfully ban gayi!\n\n"
            "🎬 5-second video ready hai."
        )

        with open(video_path, "rb") as video:

            await update.message.reply_video(
                video=video,
                caption="🎬 Your animation is ready!"
            )

        # Cleanup
        try:
            os.remove(image_path)
            os.remove(video_path)
        except Exception:
            pass

        context.user_data.clear()

    except Exception as e:

        logging.exception(
            "Animation generation failed"
        )

        await update.message.reply_text(
            "❌ Animation generate nahi ho payi.\n\n"
            f"Error: {e}\n\n"
            "Image dobara bhejkar try karein."
        )


# -----------------------------
# MAIN
# -----------------------------

def main():

    if not TOKEN:
        raise ValueError(
            "BOT_TOKEN environment variable missing"
        )

    if not REPLICATE_TOKEN:
        raise ValueError(
            "REPLICATE_API_TOKEN environment variable missing"
        )

    # Render web server
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # Telegram application
    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    # Commands
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Images
    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo
        )
    )

    # Text prompts
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )

    print(
        "Telegram bot with animation processing "
        "is running..."
    )

    app.run_polling()


if __name__ == "__main__":
    main()
