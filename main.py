import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

# --- الإعدادات الأساسية ---
# استبدل 'YOUR_BOT_TOKEN' بالتوكن الخاص ببوتك أو استخدم متغيرات البيئة في Koyeb
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN')

# --- الدوال الأساسية للبوت ---

async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هذه الدالة الرئيسية التي تعالج جميع الرسائل التي تحتوي على مستندات في الدردشات الخاصة.
    تقوم بإضافة جميع المستندات إلى قائمة انتظار لإعادة إرسالها كمقاطع صوتية.
    """
    print(f"DEBUG: تم استدعاء دالة handle_documents لرسالة من الدردشة {update.effective_chat.id}")
    print(f"DEBUG: محتوى الرسالة: {update.message}")

    message = update.message
    
    # *** التغيير هنا: تم إزالة الفحص is_audio_document. ***
    # الآن، أي مستند يتم استلامه سيتم إضافته مباشرة إلى قائمة الانتظار
    # لمحاولة إعادة إرساله كملف صوتي.

    # إذا كانت هذه أول رسالة في دفعة، نبدأ مؤقتاً
    if 'file_queue' not in context.user_data:
        context.user_data['file_queue'] = []
        # ننتظر فترة قصيرة (1.5 ثانية) لتجميع كل الملفات التي قد تصل في الألبوم
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

    print(f"DEBUG: سيتم معالجة {len(messages)} ملف.")
    # فرز الرسائل بناءً على معرف الرسالة للحفاظ على الترتيب
    messages.sort(key=lambda m: m.message_id)

    # إرسال رسالة للمستخدم لإعلامه ببدء المعالجة
    await update.effective_chat.send_message(f"تم استلام {len(messages)} ملف. جاري إعادة الإرسال...")

    for message in messages:
        print(f"DEBUG: فحص الرسالة ID: {message.message_id}")
        file_id_to_send = None
        file_name = "ملف غير معروف" # تم تغيير النص الافتراضي

        # نحاول الحصول على file_id من message.audio أولاً، ثم من message.document
        # في حال كان المستند المُرسل هو في الأصل ملف صوتي، قد يكون متاحًا كـ message.audio
        if message.audio:
            file_id_to_send = message.audio.file_id
            file_name = message.audio.file_name or "ملف صوتي"
            print(f"DEBUG: تم التعرف على ملف صوتي (message.audio): {file_name}")
        elif message.document: # الآن نتحقق من أي مستند
            file_id_to_send = message.document.file_id
            file_name = message.document.file_name or "مستند"
            print(f"DEBUG: تم التعرف على مستند: {file_name} (نوع MIME: {message.document.mime_type if message.document.mime_type else 'غير معروف'})")
        else:
            # هذا الشرط لا ينبغي أن يتم الوصول إليه، لأن الفلتر الخارجي يضمن وجود مستند.
            print(f"DEBUG: الرسالة ID: {message.message_id} ليست مستندًا. (خطأ فلترة غير متوقع).")
            continue

        if file_id_to_send:
            try:
                print(f"DEBUG: محاولة إعادة إرسال الملف {file_name} كملف صوتي بمعرف {file_id_to_send}")
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=file_id_to_send
                )
                print(f"DEBUG: تم إعادة إرسال الملف {file_name} بنجاح كملف صوتي.")
            except Exception as e:
                print(f"ERROR: حدث خطأ أثناء محاولة إعادة إرسال الملف {file_name} كملف صوتي: {e}")
                # إبلاغ المستخدم بوجود مشكلة في التحويل إذا لم يكن الملف صوتيًا
                await update.effective_chat.send_message(f"عفواً، حدث خطأ أثناء معالجة المستند: '{file_name}'. (ربما ليس ملفاً صوتياً قابلاً للتحويل).")
        else:
            print(f"DEBUG: لا يوجد file_id_to_send صالح للرسالة ID: {message.message_id}")
            await update.effective_chat.send_message(f"عفواً، لم أتمكن من العثور على معرّف ملف صالح للمستند ID: {message.message_id}")
    
    await update.effective_chat.send_message("✅ اكتمل الإرسال!")
    print("DEBUG: تم إرسال رسالة 'اكتمل الإرسال!'.")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    دالة ترحيبية عند إرسال /start
    """
    print(f"DEBUG: تم استدعاء أمر /start من الدردشة {update.effective_chat.id}")
    welcome_message = """
    أهلاً بك في بوت إعادة إرسال المستندات كمقاطع صوتية! 🎶

    أرسل لي أي مستند في محادثة خاصة، وسأحاول إعادة إرساله لك كمقطع صوتي.
    إذا كان المستند غير صوتي، قد يحدث خطأ في التحويل.
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

    # إضافة معالج لجميع المستندات في المحادثات الخاصة
    # الفلتر الآن هو filters.Document (أي نوع من المستندات) و filters.ChatType.PRIVATE (دردشة خاصة)
    # لا يوجد فحص مسبق لنوع MIME هنا، سيتم المحاولة مباشرة لإعادة الإرسال كـ audio.
    application.add_handler(MessageHandler(
        filters.Document # الرسالة يجب أن تكون مستندًا (أي نوع من المستندات)
        & filters.ChatType.PRIVATE, # ويجب أن تكون في محادثة خاصة
        handle_documents # تم تغيير اسم الدالة لتعكس أنها تعالج جميع المستندات
    ))

    # تشغيل البوت
    print("DEBUG: بدء تشغيل البوت (polling).")
    application.run_polling()
    print("DEBUG: تم إيقاف تشغيل البوت.")


if __name__ == '__main__':
    main()
