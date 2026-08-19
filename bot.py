import os
import logging
import threading
import tempfile
import requests

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import replicate


# =========================
# LOGGING
# =========================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# =========================
# ENVIRONMENT VARIABLES
# =========================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
REPLICATE_API_TOKEN = os.environ.get("REPLICATE_API_TOKEN")


# =========================
# CHECK TOKENS
# =========================

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable missing")

if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN environment variable missing")


# Replicate model
MODEL = "wavespeedai/wan-2.1-i2v-480p"


# =========================
# RENDER HEALTH SERVER
# =========================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Telegram animation bot is running!")

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


# =========================
# START COMMAND
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    context.user_data["image_url"] = None
    context.user_data["waiting_for_prompt"] = False

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "📷 Pehle ek image bhejiye.\n"
        "Uske baad main animation prompt maangunga.\n\n"
        "🎬 Image + Prompt se animation video banegi."
    )


# =========================
# IMAGE RECEIVER
# =========================

async def handle_photo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.photo:
        return

    try:

        await update.message.reply_text(
            "📥 Image mil gayi!\n\n"
            "⏳ Image prepare kar raha hoon..."
        )

        photo = update.message.photo[-1]

        file = await context.bot.get_file(photo.file_id)

        # Temporary file
        temp_path = os.path.join(
            tempfile.gettempdir(),
            f"telegram_image_{update.message.from_user.id}.jpg"
        )

        await file.download_to_drive(temp_path)

        # Replicate client
        client = replicate.Client(
            api_token=REPLICATE_API_TOKEN
        )

        # Upload image to Replicate
        with open(temp_path, "rb") as image_file:

            uploaded_image = client.files.create(
                file=image_file,
                purpose="input"
            )

        image_url = uploaded_image.urls.get("get")

        if not image_url:
            raise Exception("Image upload URL nahi mila.")

        context.user_data["image_url"] = image_url
        context.user_data["waiting_for_prompt"] = True

        await update.message.reply_text(
            "✅ Image ready hai!\n\n"
            "📝 Ab animation prompt bhejiye.\n\n"
            "Example:\n"
            "Slowly move the camera forward. "
            "Keep the characters and background consistent. "
            "Natural subtle movement, cinematic motion, "
            "realistic lighting, 5 seconds, 16:9."
        )

        try:
            os.remove(temp_path)
        except Exception:
            pass

    except Exception as e:

        logging.exception("Image processing error")

        await update.message.reply_text(
            f"❌ Image process nahi ho payi.\n\n"
            f"Error: {e}"
        )


# =========================
# PROMPT + VIDEO GENERATION
# =========================

async def handle_prompt(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    image_url = context.user_data.get("image_url")
    waiting = context.user_data.get(
        "waiting_for_prompt",
        False
    )

    # Agar image nahi hai
    if not image_url or not waiting:

        await update.message.reply_text(
            "📷 Pehle image bhejiye.\n"
            "Uske baad animation prompt bhejiye."
        )

        return

    # Prompt length check
    if len(text) < 10:

        await update.message.reply_text(
            "⚠️ Prompt thoda detail mein bhejiye."
        )

        return

    context.user_data["waiting_for_prompt"] = False

    await update.message.reply_text(
        "🎬 Animation processing start ho gayi!\n\n"
        "⏳ Replicate image ko video mein convert kar raha hai.\n"
        "Thoda time lag sakta hai..."
    )

    try:

        client = replicate.Client(
            api_token=REPLICATE_API_TOKEN
        )

        # =========================
        # REPLICATE VIDEO GENERATION
        # =========================

        output = client.run(
            MODEL,
            input={
                "image": image_url,
                "prompt": text,
                "aspect_ratio": "16:9",
                "negative_prompt": (
                    "distorted face, deformed body, "
                    "extra limbs, duplicate people, "
                    "flickering, sudden scene change, "
                    "camera shake, blurry image"
                )
            }
        )

        # Output URL
        if hasattr(output, "url"):
            video_url = output.url()
        elif isinstance(output, str):
            video_url = output
        else:
            video_url = str(output)

        await update.message.reply_text(
            "✅ Animation ready ho gayi!\n\n"
            "📤 Video Telegram par bhej raha hoon..."
        )

        # =========================
        # DOWNLOAD VIDEO
        # =========================

        video_response = requests.get(
            video_url,
            timeout=180
        )

        video_response.raise_for_status()

        video_path = os.path.join(
            tempfile.gettempdir(),
            f"animation_{update.message.from_user.id}.mp4"
        )

        with open(video_path, "wb") as video_file:
            video_file.write(video_response.content)

        # =========================
        # SEND VIDEO
        # =========================

        with open(video_path, "rb") as video_file:

            await update.message.reply_video(
                video=video_file,
                caption=(
                    "🎬 Animation complete!\n\n"
                    "📐 16:9\n"
                    "✨ Image-to-video generation"
                ),
                supports_streaming=True
            )

        # Cleanup
        try:
            os.remove(video_path)
        except Exception:
            pass

        context.user_data["image_url"] = None

        await update.message.reply_text(
            "📷 Nayi animation ke liye "
            "dobara image bhejiye."
        )

    except Exception as e:

        logging.exception("Video generation error")

        context.user_data["waiting_for_prompt"] = True

        await update.message.reply_text(
            "❌ Animation generate nahi ho payi.\n\n"
            f"Error: {e}\n\n"
            "Aap prompt dobara bhej sakte hain."
        )


# =========================
# MAIN
# =========================

def main():

    # Render web server
    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True
    )

    web_thread.start()

    # Telegram application
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Photos
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
            handle_prompt
        )
    )

    print("Telegram animation bot is running...")

    app.run_polling()


# =========================
# RUN
# =========================

if __name__ == "__main__":
    main()
