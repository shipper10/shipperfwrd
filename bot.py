import os
import threading
import time
import requests
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")  # ضع التوكن هنا أو في متغير بيئة

# -----------------------------
# متغير مؤقت لتخزين الملفات المستلمة
# -----------------------------
user_batches = {}  # {user_id: [list_of_files]}

# -----------------------------
# أوامر البوت
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل دفعة ملفات، وعندما تنتهي أرسل كلمة: تم ✅")

async def handle_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file_info = None

    # تحديد نوع الملف
    if update.message.document:
        file_info = update.message.document.file_id
    elif update.message.audio:
        file_info = update.message.audio.file_id
    elif update.message.voice:
        file_info = update.message.voice.file_id
    elif update.message.video:
        file_info = update.message.video.file_id
    elif update.message.photo:
        file_info = update.message.photo[-1].file_id  # أكبر جودة للصورة

    if file_info:
        user_batches.setdefault(user_id, []).append(file_info)
        await update.message.reply_text(f"📥 تم استلام ملف رقم {len(user_batches[user_id])}")

async def finish_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_batches or not user_batches[user_id]:
        await update.message.reply_text("❌ لا يوجد ملفات محفوظة")
        return

    await update.message.reply_text("🔄 جاري إرسال الملفات بالترتيب...")
    for file_id in user_batches[user_id]:
        try:
            await update.message.reply_document(file_id)
        except:
            try:
                await update.message.reply_photo(file_id)
            except:
                try:
                    await update.message.reply_audio(file_id)
                except:
                    await update.message.reply_video(file_id)

    # مسح الملفات بعد الإرسال
    user_batches[user_id] = []

# -----------------------------
# تشغيل البوت
# -----------------------------
def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("(?i)تم"), finish_batch))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.AUDIO | filters.VOICE | filters.VIDEO | filters.PHOTO, handle_files))

    app.run_polling()

# -----------------------------
# Flask Keep-Alive
# -----------------------------
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "I am alive"

def run_flask():
    flask_app.run(host="0.0.0.0", port=8000)

def keep_alive_ping():
    url = "http://127.0.0.1:8000"
    while True:
        try:
            requests.get(url)
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(300)  # كل 5 دقائق

# -----------------------------
# تشغيل الكل
# -----------------------------
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    threading.Thread(target=run_flask).start()
    threading.Thread(target=keep_alive_ping).start()
