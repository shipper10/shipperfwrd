import os
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.easyid3 import EasyID3

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
cover_image = None

async def set_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        file = await update.message.reply_to_message.photo[-1].get_file()
        image_bytes = await file.download_as_bytearray()
        global cover_image
        cover_image = bytes(image_bytes)
        await update.message.reply_text("✅ تم تعيين الغلاف المخصص بنجاح من الرد.")
    else:
        await update.message.reply_text("أرسل الآن الصورة أو قم بالرد على صورة بـ /setcover")
        context.user_data['waiting_for_cover'] = True

async def clear_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global cover_image
    cover_image = None
    await update.message.reply_text("تم مسح الغلاف المخصص. سيتم استخدام الغلاف الأصلي من الملفات.")

def extract_cover_from_mp3(file_path):
    try:
        audio = MP3(file_path, ID3=ID3)
        for tag in audio.tags.values():
            if isinstance(tag, APIC):
                return tag.data
    except Exception:
        return None
    return None

def extract_id3_tags(file_path):
    try:
        audio = EasyID3(file_path)
        title = audio.get("title", [None])[0]
        artist = audio.get("artist", [None])[0]
        album = audio.get("album", [None])[0]
        return title, artist, album
    except Exception:
        return None, None, None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global cover_image
    if context.user_data.get('waiting_for_cover'):
        file = await update.message.photo[-1].get_file()
        image_bytes = await file.download_as_bytearray()
        cover_image = bytes(image_bytes)
        context.user_data['waiting_for_cover'] = False
        await update.message.reply_text("✅ تم تعيين الغلاف المخصص بنجاح.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global cover_image
    file = await update.message.document.get_file()
    file_path = "temp.mp3"
    await file.download_to_drive(file_path)

    # قراءة البيانات من الملف
    title, artist, album = extract_id3_tags(file_path)

    # إعداد الغلاف
    if cover_image:
        thumb_bytes = io.BytesIO(cover_image)
    else:
        cover = extract_cover_from_mp3(file_path)
        thumb_bytes = io.BytesIO(cover) if cover else None

    await context.bot.send_audio(
        chat_id=update.effective_chat.id,
        audio=open(file_path, 'rb'),
        title=title or update.message.document.file_name,
        performer=artist or None,
        thumbnail=thumb_bytes if thumb_bytes else None
    )
    os.remove(file_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "أرسل مستند MP3 وسأعيد إرساله كمقطع صوتي بنفس البيانات والكوفر.\n"
        "استخدم /setcover لتعيين غلاف مخصص (أو رد على صورة بـ /setcover)، و /clearcover لمسحه."
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setcover", set_cover))
    app.add_handler(CommandHandler("clearcover", clear_cover))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.MP3, handle_document))
    app.run_polling()

if __name__ == "__main__":
    main()
