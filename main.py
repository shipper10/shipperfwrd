import os
import asyncio
from telegram import Update, InputFile
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from mutagen.id3 import ID3, APIC
from tempfile import NamedTemporaryFile

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
                local_path = await file.download_to_drive()

                title = performer = album = genre = year = None
                thumb_file = None

                try:
                    id3_tags = ID3(local_path.name)
                    title = id3_tags.get('TIT2').text[0] if id3_tags.get('TIT2') else None
                    performer = id3_tags.get('TPE1').text[0] if id3_tags.get('TPE1') else None
                    album = id3_tags.get('TALB').text[0] if id3_tags.get('TALB') else None
                    genre = id3_tags.get('TCON').text[0] if id3_tags.get('TCON') else None
                    year = id3_tags.get('TDRC').text[0] if id3_tags.get('TDRC') else None

                    apic = id3_tags.getall('APIC')
                    if apic:
                        img_data = apic[0].data
                        tmp_thumb = NamedTemporaryFile(delete=False)
                        tmp_thumb.write(img_data)
                        tmp_thumb.close()
                        thumb_file = tmp_thumb.name
                except Exception:
                    pass

                with open(local_path.name, 'rb') as f:
                    await context.bot.send_audio(
                        chat_id=update.effective_chat.id,
                        audio=f,
                        filename=message.document.file_name,
                        title=title,
                        performer=performer,
                        thumbnail=InputFile(thumb_file) if thumb_file else None
                    )

                details = ""
                if title:
                    details += f"🎵 **العنوان:** {title}\n"
                if performer:
                    details += f"👤 **الفنان:** {performer}\n"
                if album:
                    details += f"💿 **الألبوم:** {album}\n"
                if genre:
                    details += f"🎼 **النوع:** {genre}\n"
                if year:
                    details += f"📅 **السنة:** {year}\n"
                if details:
                    await update.effective_chat.send_message(details)

            except Exception as e:
                await update.effective_chat.send_message(f"❌ حدث خطأ أثناء إعادة إرسال الملف '{message.document.file_name}': {e}")
    await update.effective_chat.send_message("✅ اكتمل الإرسال!")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أرسل لي أي مستند MP3 في محادثة خاصة، وسأعيد إرساله لك كمقطع صوتي مع جميع بياناته وصورة الغلاف من التاج ID3 إن وجدت."
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.ALL, handle_documents))
    application.run_polling()

if __name__ == '__main__':
    main()
