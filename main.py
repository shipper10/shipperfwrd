import asyncio
import sqlite3
from telethon import TelegramClient, events
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

# ---------- إعدادات الاتصال ----------
API_ID = int(os.getenv("API_ID"))  # من my.telegram.org
API_HASH = os.getenv("API_HASH")   # من my.telegram.org
SESSION_STRING = os.getenv("SESSION_STRING")  # من Telethon (String Session)
BOT_TOKEN = os.getenv("BOT_TOKEN")  # من BotFather
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))  # ID المجموعة الهدف

# ---------- إنشاء قاعدة البيانات ----------
conn = sqlite3.connect("filters.db")
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY,
    filter_enabled INTEGER DEFAULT 0,
    media_types TEXT DEFAULT ''
)""")
cur.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")

cur.execute("""CREATE TABLE IF NOT EXISTS allowed_keywords (word TEXT UNIQUE)""")
cur.execute("""CREATE TABLE IF NOT EXISTS blocked_keywords (word TEXT UNIQUE)""")
cur.execute("""CREATE TABLE IF NOT EXISTS ignored_sources (source TEXT UNIQUE)""")
cur.execute("""CREATE TABLE IF NOT EXISTS always_send_sources (source TEXT UNIQUE)""")

conn.commit()

# ---------- دوال قاعدة البيانات ----------
def update_setting(name, value):
    cur.execute(f"UPDATE settings SET {name} = ? WHERE id = 1", (value,))
    conn.commit()

def get_settings():
    cur.execute("SELECT filter_enabled, media_types FROM settings WHERE id = 1")
    return cur.fetchone()

def add_to_table(table, value):
    cur.execute(f"INSERT OR IGNORE INTO {table} VALUES (?)", (value.lower(),))
    conn.commit()

def remove_from_table(table, value):
    cur.execute(f"DELETE FROM {table} WHERE word = ? OR source = ?", (value.lower(), value.lower()))
    conn.commit()

def get_list(table):
    cur.execute(f"SELECT * FROM {table}")
    return [row[0] for row in cur.fetchall()]

# ---------- عميل Telethon ----------
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@client.on(events.NewMessage)
async def handler(event):
    try:
        settings = get_settings()
        filter_enabled, media_types = settings
        media_types = media_types.split(",") if media_types else []

        sender = await event.get_sender()
        chat = await event.get_chat()

        # اسم القناة أو معرفها
        source_name = getattr(chat, "username", None) or chat.id

        # تحقق من القنوات المستثناة
        if source_name in get_list("ignored_sources"):
            return

        # تحقق من القنوات الإجبارية
        always_send = source_name in get_list("always_send_sources")

        text = event.raw_text.lower() if event.raw_text else ""
        media_type = "نص"
        if event.photo:
            media_type = "صورة"
        elif event.video:
            media_type = "فيديو"
        elif event.audio or event.voice:
            media_type = "صوت"
        elif event.document:
            media_type = "ملف"

        # فلترة
        if filter_enabled and not always_send:
            allowed = get_list("allowed_keywords")
            blocked = get_list("blocked_keywords")

            # الكلمات الممنوعة
            if any(word in text for word in blocked):
                return

            # الكلمات المسموحة
            if allowed and not any(word in text for word in allowed):
                return

            # أنواع الوسائط
            if media_types and media_type not in media_types:
                return

        # إعادة التوجيه
        await client.forward_messages(TARGET_CHAT_ID, event.message)
    except Exception as e:
        print(f"Error: {e}")

# ---------- أوامر البوت ----------
async def filter_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_setting("filter_enabled", 1)
    await update.message.reply_text("✅ تم تفعيل الفلترة.")

async def filter_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_setting("filter_enabled", 0)
    await update.message.reply_text("🚫 تم إيقاف الفلترة.")

async def set_allowed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = " ".join(context.args).split(",")
    for w in words:
        add_to_table("allowed_keywords", w.strip())
    await update.message.reply_text("✅ تم تحديث الكلمات المسموحة.")

async def set_blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    words = " ".join(context.args).split(",")
    for w in words:
        add_to_table("blocked_keywords", w.strip())
    await update.message.reply_text("✅ تم تحديث الكلمات الممنوعة.")

async def set_media_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    types = " ".join(context.args).split(",")
    update_setting("media_types", ",".join([t.strip() for t in types]))
    await update.message.reply_text("✅ تم تحديث أنواع الوسائط المسموحة.")

async def add_ignore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_to_table("ignored_sources", context.args[0])
    await update.message.reply_text("🚫 تم استثناء القناة.")

async def remove_ignore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remove_from_table("ignored_sources", context.args[0])
    await update.message.reply_text("✅ تم إزالة الاستثناء.")

async def add_always(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_to_table("always_send_sources", context.args[0])
    await update.message.reply_text("📌 تم إضافة القناة للإرسال الإجباري.")

async def remove_always(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remove_from_table("always_send_sources", context.args[0])
    await update.message.reply_text("✅ تم إزالة الإرسال الإجباري.")

async def filter_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = get_settings()
    filter_enabled, media_types = settings
    text = f"""
📊 **حالة الفلترة**:
- الفلترة: {"✅ مفعلة" if filter_enabled else "🚫 متوقفة"}
- الكلمات المسموحة: {", ".join(get_list("allowed_keywords")) or "لا يوجد"}
- الكلمات الممنوعة: {", ".join(get_list("blocked_keywords")) or "لا يوجد"}
- الوسائط المسموحة: {media_types or "الكل"}
- القنوات المستثناة: {", ".join(get_list("ignored_sources")) or "لا يوجد"}
- القنوات الإجبارية: {", ".join(get_list("always_send_sources")) or "لا يوجد"}
"""
    await update.message.reply_text(text)

# ---------- تشغيل البوت و Telethon ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("filter_on", filter_on))
    app.add_handler(CommandHandler("filter_off", filter_off))
    app.add_handler(CommandHandler("set_allowed", set_allowed))
    app.add_handler(CommandHandler("set_blocked", set_blocked))
    app.add_handler(CommandHandler("set_media_types", set_media_types))
    app.add_handler(CommandHandler("add_ignore", add_ignore))
    app.add_handler(CommandHandler("remove_ignore", remove_ignore))
    app.add_handler(CommandHandler("add_always", add_always))
    app.add_handler(CommandHandler("remove_always", remove_always))
    app.add_handler(CommandHandler("filter_status", filter_status))

    await asyncio.gather(
        app.run_polling(),
        client.start()
    )

if __name__ == "__main__":
    asyncio.run(main())
