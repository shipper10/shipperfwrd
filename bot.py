from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import os

# بيئة التشغيل
TOKEN = os.getenv("TOKEN", "ضع_التوكن_هنا")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://APPNAME.koyeb.app")  # غير APPNAME باسم تطبيقك

# تخزين الملفات مؤقتاً لكل مستخدم
user_batches = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي دفعة ملفات MP3 وسأعيدها كمقاطع موسيقية بنفس الترتيب 🎵")

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # إذا الملف MP3
    if update.message.document and update.message.document.mime_type == "audio/mpeg":
        if user_id not in user_batches:
            user_batches[user_id] = []

        # تخزين ترتيب الملفات
        user_batches[user_id].append(update.message.document.file_id)

        await update.message.reply_text(f"تم استلام الملف {len(user_batches[user_id])} 🎶\n"
                                        "أرسل باقي الملفات أو اكتب /send لإرسالها.")
    else:
        await update.message.reply_text("أرسل ملف MP3 فقط.")

async def send_batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_batches and user_batches[user_id]:
        await update.message.reply_text("جارٍ إرسال الملفات بالترتيب 🎼")
        for file_id in user_batches[user_id]:
            await update.message.reply_audio(audio=file_id)
        user_batches[user_id] = []
    else:
        await update.message.reply_text("لا يوجد ملفات لإرسالها.")

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", send_batch))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_audio))

    # تشغيل البوت على Koyeb بالويب هوك
    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
