import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# --- الإعدادات الأساسية ---
# استبدل 'YOUR_BOT_TOKEN' بالتوكن الخاص ببوتك أو استخدم متغيرات البيئة في Koyeb
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN')

# --- الدوال الأساسية للبوت ---

async def handle_audio_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هذه الدالة الرئيسية التي تعالج الرسائل التي تحتوي على ملفات.
    تنتظر قليلاً لتجميع كل الملفات التي قد تصل في دفعة واحدة (ألبوم).
    """
    # إذا كانت هذه أول رسالة في دفعة، نبدأ مؤقتاً
    if 'file_queue' not in context.user_data:
        context.user_data['file_queue'] = []
        # ننتظر فترة قصيرة (1.5 ثانية) لتجميع كل الملفات في الألبوم
        asyncio.create_task(process_file_queue(update, context))

    # نضيف الرسالة الحالية إلى قائمة الانتظار
    context.user_data['file_queue'].append(update.message)


async def process_file_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    بعد انتهاء فترة الانتظار، تبدأ هذه الدالة في معالجة الملفات المجمعة.
    """
    await asyncio.sleep(1.5)  # انتظار لتجميع كل الملفات

    messages = context.user_data.pop('file_queue', [])
    if not messages:
        return

    # فرز الرسائل بناءً على معرف الرسالة للحفاظ على الترتيب
    messages.sort(key=lambda m: m.message_id)

    # إرسال رسالة للمستخدم لإعلامه ببدء المعالجة
    await update.effective_chat.send_message(f"تم استلام {len(messages)} ملف. جاري إعادة الإرسال...")

    for message in messages:
        # نتأكد أن الرسالة تحتوي على ملف وأن نوعه mp3
        if message.document and message.document.mime_type == 'audio/mpeg':
            try:
                # ببساطة نعيد إرسال الملف الصوتي باستخدام معرّف الملف (file_id)
                # تليجرام سيقوم تلقائياً بمعالجته كملف صوتي قابل للتشغيل
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=message.document.file_id
                )
            except Exception as e:
                print(f"حدث خطأ: {e}")
                await update.effective_chat.send_message(f"عفواً، حدث خطأ أثناء معالجة الملف: {message.document.file_name}")
    
    await update.effective_chat.send_message("✅ اكتمل الإرسال!")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    دالة ترحيبية عند إرسال /start
    """
    welcome_message = """
    أهلاً بك في بوت إعادة إرسال MP3! 🎶

    أرسل لي ملف MP3 أو مجموعة ملفات (ألبوم) وسأقوم بإعادة إرسالها لك كمقاطع صوتية قابلة للتشغيل مباشرة مع الحفاظ على بياناتها الأصلية.
    """
    await update.message.reply_text(welcome_message)


# --- تشغيل البوت ---
def main():
    """
    الدالة الرئيسية لتشغيل البوت.
    """
    print("البوت قيد التشغيل...")
    
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة معالج الأوامر
    application.add_handler(CommandHandler("start", start_command))

    # إضافة معالج للملفات (Documents) من نوع mp3
    application.add_handler(MessageHandler(filters.Document.MIME_TYPE & filters.ChatType.PRIVATE, handle_audio_files))

    # تشغيل البوت
    application.run_polling()


if __name__ == '__main__':
    main()
