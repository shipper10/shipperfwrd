import os
import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler

BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")

async def handle_documents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.chat or message.chat.type != 'private':
        return
    if not message.document:
        return
    if 'file_queue' not in context.user_data:
        context.user_data['file_queue'] = []
        asyncio.create_task(process_file_queue(update, context))
    context.user_data['file_queue'].append(message)

async def process_file_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(1.5)
    messages = context.user_data.pop('file_queue', [])
    if not messages:
        return
    messages.sort(key=lambda m: m.message_id)
    await update.effective_chat.send_message(f"تم استلام {len(messages)} ملف. جاري إعادة الإرسال...")
    for message in messages:
        if message.document:
            try:
                file = await context.bot.get_file(message.document.file_id)
                file_path = file.file_path
                # تحميل الملف وإرساله كمقطع صوتي من خلال البيانات الثنائية بدلاً من الرابط
                new_file = await file.download_to_drive()
                with open(new_file.name, 'rb') as f:
                    await context.bot.send_audio(
                        chat_id=update.effective_chat.id,
                        audio=f
                    )
            except Exception as e:
                await update.effective_chat.send_message(f"❌ حدث خطأ أثناء إعادة إرسال الملف '{message.document.file_name}': {e}")
    await update.effective_chat.send_message("✅ اكتمل الإرسال!")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أرسل لي أي مستند في محادثة خاصة، وسأعيد إرساله لك كمقطع صوتي قابل للتشغيل."
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.ALL, handle_documents))
    application.run_polling()

if __name__ == '__main__':
    main()
