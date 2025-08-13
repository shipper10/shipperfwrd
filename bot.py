import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio
from collections import defaultdict

TOKEN = os.getenv("TOKEN", "ضع_التوكن_هنا")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# تخزين مؤقت لدفعات الملفات
user_batches = defaultdict(list)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أرسل دفعة من ملفات MP3 🎵 وسأعيدها لك كمقاطع موسيقية بنفس الترتيب.\n"
        "بعد ما تخلص الإرسال، أرسل الأمر /done لبدء المعالجة."
    )

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # دعم إرسال الملف كمستند أو كمقطع صوتي
    if update.message.document and update.message.document.mime_type == "audio/mpeg":
        user_batches[user_id].append(update.message.document.file_id)
        await update.message.reply_text(f"📥 تمت إضافة الملف {update.message.document.file_name} للدفعة.")
    elif update.message.audio:
        user_batches[user_id].append(update.message.audio.file_id)
        await update.message.reply_text(f"📥 تمت إضافة الملف {update.message.audio.file_name} للدفعة.")
    else:
        await update.message.reply_text("⚠ أرسل ملف MP3 فقط.")

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_batches[user_id]:
        await update.message.reply_text("⚠ لا يوجد ملفات في الدفعة.")
        return

    await update.message.reply_text("⏳ جاري إرسال الملفات بالترتيب...")

    for file_id in user_batches[user_id]:
        await update.message.reply_audio(audio=file_id)

    user_batches[user_id].clear()
    await update.message.reply_text("✅ تم إرسال جميع الملفات بالترتيب.")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("done", done))
application.add_handler(MessageHandler(filters.ALL, handle_audio))

# ويب هوك
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok", 200

# هيلث شيك
@app.route('/')
def index():
    return "Bot is running!", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
