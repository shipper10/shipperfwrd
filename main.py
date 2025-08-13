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
    هذه الدالة الرئيسية التي تعالج الرسائل التي تحتوي على ملفات صوتية (كمستندات).
    تنتظر قليلاً لتجميع كل الملفات التي قد تصل في دفعة واحدة (ألبوم).

    ملاحظة: هذه الدالة لن تُستدعى إلا إذا كانت الرسالة مستندًا صوتيًا في دردشة خاصة،
    بفضل الفلتر المخصص في MessageHandler.
    """
    print(f"DEBUG: تم استدعاء دالة handle_audio_files لرسالة من الدردشة {update.effective_chat.id}")
    print(f"DEBUG: محتوى الرسالة: {update.message}")

    # بما أن الفلتر الخارجي يضمن أن الرسالة هي مستند صوتي في محادثة خاصة،
    # لا نحتاج إلى إجراء فحوصات إضافية هنا لنوع الدردشة أو نوع الملف الأساسي.
    message = update.message

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
    print("DEBUG: بدء انتظار 1.5 ثانية لمعالجة قائمة الملفات.")
    await asyncio.sleep(1.5)  # انتظار لتجميع كل الملفات

    messages = context.user_data.pop('file_queue', [])
    if not messages:
        print("DEBUG: قائمة الملفات فارغة بعد الانتظار. لا يوجد شيء لمعالجته.")
        return

    print(f"DEBUG: سيتم معالجة {len(messages)} رسالة.")
    # فرز الرسائل بناءً على معرف الرسالة للحفاظ على الترتيب
    messages.sort(key=lambda m: m.message_id)

    # إرسال رسالة للمستخدم لإعلامه ببدء المعالجة
    await update.effective_chat.send_message(f"تم استلام {len(messages)} ملف. جاري إعادة الإرسال...")

    for message in messages:
        print(f"DEBUG: فحص الرسالة ID: {message.message_id}")
        file_id_to_send = None
        file_name = "ملف صوتي غير معروف"

        # بما أن الفلتر الخارجي يضمن أنها مستند صوتي، يمكننا الاعتماد على message.document هنا.
        # ولكن أضفت فحص message.audio كـ "تأمين" إضافي في حال أرسل تيليجرام نفس الملف كـ 'audio' أيضاً.
        if message.audio: # قد يكون المستند الصوتي قد تم إرساله كـ 'audio' من قبل تيليجرام
            file_id_to_send = message.audio.file_id
            file_name = message.audio.file_name or "ملف صوتي"
            print(f"DEBUG: تم التعرف على ملف صوتي (message.audio): {file_name}")
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('audio/'):
            file_id_to_send = message.document.file_id
            file_name = message.document.file_name or "ملف صوتي"
            print(f"DEBUG: تم التعرف على ملف صوتي (message.document) من نوع: {message.document.mime_type}, الاسم: {file_name}")
        else:
            # هذا الشرط لا ينبغي أن يتم الوصول إليه بوجود الفلتر الجديد الدقيق،
            # لكن نتركه للتأكد من المرونة.
            print(f"DEBUG: الرسالة ID: {message.message_id} ليست ملف صوتي أو مستند صوتي. (خطأ فلترة غير متوقع).")
            # لا نرسل رسالة خطأ هنا لأن الفلتر الخارجي سيتولى عدم استدعاء الدالة.
            continue

        if file_id_to_send:
            try:
                print(f"DEBUG: محاولة إعادة إرسال الملف الصوتي: {file_name} بمعرف {file_id_to_send}")
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=file_id_to_send
                )
                print(f"DEBUG: تم إعادة إرسال الملف الصوتي: {file_name} بنجاح.")
            except Exception as e:
                print(f"ERROR: حدث خطأ أثناء إعادة إرسال الملف {file_name}: {e}")
                await update.effective_chat.send_message(f"عفواً، حدث خطأ أثناء معالجة الملف: {file_name}")
        else:
            print(f"DEBUG: لا يوجد file_id_to_send صالح للرسالة ID: {message.message_id}")
    
    await update.effective_chat.send_message("✅ اكتمل الإرسال!")
    print("DEBUG: تم إرسال رسالة 'اكتمل الإرسال!'.")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    دالة ترحيبية عند إرسال /start
    """
    print(f"DEBUG: تم استدعاء أمر /start من الدردشة {update.effective_chat.id}")
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

    # إضافة معالج للرسائل التي هي مستندات صوتية في محادثة خاصة فقط
    # يتم دمج الفلاتر مباشرة باستخدام عامل التشغيل '&'
    application.add_handler(MessageHandler(
        filters.Document # الرسالة يجب أن تكون مستندًا
        & filters.MimeType('audio/*') # ونوع MIME الخاص بها يجب أن يكون صوتيًا
        & filters.ChatType.PRIVATE, # ويجب أن تكون في محادثة خاصة
        handle_audio_files
    ))

    # تشغيل البوت
    print("DEBUG: بدء تشغيل البوت (polling).")
    application.run_polling()
    print("DEBUG: تم إيقاف تشغيل البوت.")


if __name__ == '__main__':
    main()
