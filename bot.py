import os
import uuid
import asyncio
from collections import deque
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # رابط Koyeb

queue = deque()
processing = False

# Telegram application
application = Application.builder().token(TOKEN).build()

async def process_queue(context: ContextTypes.DEFAULT_TYPE):
    global processing
    while queue:
        chat_id, file_id, file_name = queue.popleft()
        try:
            ext = os.path.splitext(file_name)[1].lower()
            temp_filename = f"{uuid.uuid4()}{ext}"

            file = await context.bot.get_file(file_id)
            await file.download_to_drive(temp_filename)

            with open(temp_filename, "rb") as audio:
                await context.bot.send_audio(chat_id=chat_id, audio=audio)

            os.remove(temp_filename)
        except Exception as e:
            await context.bot.send_message(chat_id, f"❌ خطأ: {e}")
        await asyncio.sleep(0.2)
    processing = False

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global processing
    if update.message.document:
        queue.append((
            update.message.chat_id,
            update.message.document.file_id,
            update.message.document.file_name
        ))
        if not processing:
            processing = True
            await process_queue(context)
    else:
        await update.message.reply_text("📄 أرسل لي ملف MP3 وسأحوله لموسيقى.")

application.add_handler(MessageHandler(filters.Document.AUDIO, handle_document))

# Flask app
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Bot is alive!", 200

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok", 200

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: asyncio.run(application.initialize())).start()
    flask_app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
