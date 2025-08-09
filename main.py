# main.py
# بوت إدارة + تسجيل جلسات Telethon + forwarder متقدّم مع فلترة، كل شيء مخزن في SQLite.

import os
import asyncio
import sqlite3
import json
from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------- إعداد متغيرات بيئة ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # ضع ID حسابك هنا
DB_FILE = "manager_full.db"

# ---------- قاعدة البيانات ----------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

# جداول
cur.execute("""CREATE TABLE IF NOT EXISTS sessions (
    name TEXT PRIMARY KEY,
    api_id INTEGER,
    api_hash TEXT,
    session_str TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS source_channels (source TEXT PRIMARY KEY)""")
cur.execute("""CREATE TABLE IF NOT EXISTS sent_messages (msg_key TEXT PRIMARY KEY)""")

cur.execute("""CREATE TABLE IF NOT EXISTS allowed_keywords (word TEXT PRIMARY KEY)""")
cur.execute("""CREATE TABLE IF NOT EXISTS blocked_keywords (word TEXT PRIMARY KEY)""")
cur.execute("""CREATE TABLE IF NOT EXISTS ignored_sources (source TEXT PRIMARY KEY)""")
cur.execute("""CREATE TABLE IF NOT EXISTS always_send_sources (source TEXT PRIMARY KEY)""")

conn.commit()

# إعدادات افتراضية إذا لم توجد
def init_default_settings():
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("target_group", json.dumps(None)))
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("filter_enabled", json.dumps(False)))
    cur.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ("media_types", json.dumps([])))
    conn.commit()

init_default_settings()

# ---------- دوال DB مساعدة ----------
def save_session_db(name, api_id, api_hash, session_str):
    cur.execute("INSERT OR REPLACE INTO sessions (name, api_id, api_hash, session_str) VALUES (?, ?, ?, ?)",
                (name, api_id, api_hash, session_str))
    conn.commit()

def get_session_db(name):
    cur.execute("SELECT api_id, api_hash, session_str FROM sessions WHERE name = ?", (name,))
    return cur.fetchone()

def list_sessions_db():
    cur.execute("SELECT name FROM sessions")
    return [r[0] for r in cur.fetchall()]

def del_session_db(name):
    cur.execute("DELETE FROM sessions WHERE name = ?", (name,))
    conn.commit()

def set_setting(key, value):
    cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    conn.commit()

def get_setting(key):
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    return json.loads(row[0]) if row else None

def add_to_table(table, value):
    cur.execute(f"INSERT OR IGNORE INTO {table} VALUES (?)", (str(value),))
    conn.commit()

def remove_from_table_generic(table, value):
    cur.execute(f"DELETE FROM {table} WHERE {('word' if table.endswith('keywords') else 'source')} = ?", (str(value),))
    conn.commit()

def get_list_table(table):
    cur.execute(f"SELECT * FROM {table}")
    return [r[0] for r in cur.fetchall()]

def has_sent(msg_key):
    cur.execute("SELECT 1 FROM sent_messages WHERE msg_key = ?", (msg_key,))
    return cur.fetchone() is not None

def mark_sent(msg_key):
    cur.execute("INSERT OR IGNORE INTO sent_messages (msg_key) VALUES (?)", (msg_key,))
    conn.commit()

# ---------- صلاحية المدير ----------
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != ADMIN_ID:
            await update.message.reply_text("🚫 غير مصرح لك. هذا الأمر للمسؤول فقط.")
            return
        return await func(update, context)
    return wrapper

# ---------- جلسة تسجيل مؤقتة (during login) ----------
temp_login = {}  # uid -> dict(api_id, api_hash, phone, client)

# ---------- أوامر تسجيل الجلسة ----------
@admin_only
async def start_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = ("🔧 بدء إعداد تسجيل حساب شخصي.\n\n"
           "1) /set_api <API_ID> <API_HASH>\n"
           "2) /set_phone <+countryphone>\n"
           "3) بعد وصول الكود: /enter_code <CODE>\n"
           "4) إذا كان لديك 2FA: /enter_pass <PASSWORD>\n\n"
           "مثال:\n/set_api 123456 0123456789abcdef\n/set_phone +201234567890")
    await update.message.reply_text(txt)

@admin_only
async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدام: /set_api <API_ID> <API_HASH>")
        return
    api_id = int(context.args[0])
    api_hash = context.args[1]
    uid = update.effective_user.id
    temp_login.setdefault(uid, {})["api_id"] = api_id
    temp_login[uid]["api_hash"] = api_hash
    await update.message.reply_text("✅ تم حفظ API مؤقتًا. الآن أرسل رقم الهاتف عبر /set_phone")

@admin_only
async def set_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدام: /set_phone <+phone>")
        return
    phone = context.args[0]
    uid = update.effective_user.id
    info = temp_login.get(uid)
    if not info or "api_id" not in info:
        await update.message.reply_text("❗ أضف API أولًا عبر /set_api")
        return
    api_id = info["api_id"]
    api_hash = info["api_hash"]
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    try:
        await client.send_code_request(phone)
        info["phone"] = phone
        info["client"] = client
        await update.message.reply_text("✅ تم إرسال الكود. أرسله هنا باستخدام: /enter_code <CODE>")
    except Exception as e:
        await client.disconnect()
        temp_login.pop(uid, None)
        await update.message.reply_text(f"❌ خطأ أثناء إرسال الكود: {e}")

@admin_only
async def enter_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدام: /enter_code <CODE> [name_optional]")
        return
    code = context.args[0]
    name = context.args[1] if len(context.args) >= 2 else "main_account"
    uid = update.effective_user.id
    info = temp_login.get(uid)
    if not info or "client" not in info:
        await update.message.reply_text("❗ لم تبدأ العملية. استخدم /start_setup ثم /set_api و /set_phone")
        return
    client: TelegramClient = info["client"]
    phone = info["phone"]
    try:
        await client.sign_in(phone=phone, code=code)
    except errors.SessionPasswordNeededError:
        await update.message.reply_text("🔐 الحساب لديه 2FA. أرسلها باستخدام /enter_pass <PASSWORD>")
        return
    except Exception as e:
        await update.message.reply_text(f"❌ فشل تسجيل الكود: {e}")
        await client.disconnect()
        temp_login.pop(uid, None)
        return

    session_str = client.session.save()
    save_session_db(name, info["api_id"], info["api_hash"], session_str)
    await update.message.reply_text(f"✅ تم حفظ الجلسة باسم `{name}`")
    await client.disconnect()
    temp_login.pop(uid, None)

@admin_only
async def enter_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدام: /enter_pass <PASSWORD>")
        return
    pwd = " ".join(context.args)
    uid = update.effective_user.id
    info = temp_login.get(uid)
    if not info or "client" not in info:
        await update.message.reply_text("❗ لا توجد جلسة تنتظر كلمة مرور.")
        return
    client: TelegramClient = info["client"]
    try:
        await client.sign_in(password=pwd)
    except Exception as e:
        await update.message.reply_text(f"❌ فشل تسجيل كلمة المرور: {e}")
        await client.disconnect()
        temp_login.pop(uid, None)
        return
    session_str = client.session.save()
    name = "main_account"
    save_session_db(name, info["api_id"], info["api_hash"], session_str)
    await update.message.reply_text(f"✅ تم حفظ الجلسة باسم `{name}`")
    await client.disconnect()
    temp_login.pop(uid, None)

@admin_only
async def sessions_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items = list_sessions_db()
    if not items:
        await update.message.reply_text("📭 لا توجد جلسات محفوظة.")
    else:
        await update.message.reply_text("📂 الجلسات:\n" + "\n".join(items))

@admin_only
async def sessions_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدام: /del_session <name>")
        return
    name = context.args[0]
    del_session_db(name)
    await update.message.reply_text(f"🗑️ تم حذف الجلسة `{name}`")

# ---------- أوامر إدارة الفلترة والإرسال ----------
@admin_only
async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /set_target <GROUP_CHAT_ID>")
        return
    try:
        gid = int(context.args[0])
        set_setting("target_group", gid)
        await update.message.reply_text(f"✅ تم حفظ المجموعة الهدف: {gid}")
    except ValueError:
        await update.message.reply_text("❗ ID غير صالح.")

@admin_only
async def add_source_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /add_source <@username_or_id_or_invitelink>")
        return
    src = context.args[0]
    add_to_table("source_channels", src)
    await update.message.reply_text(f"✅ تمت إضافة المصدر: {src}")

@admin_only
async def remove_source_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /remove_source <source>")
        return
    remove_from_table_generic("source_channels", context.args[0])
    await update.message.reply_text("✅ تم الحذف.")

@admin_only
async def list_sources_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lst = get_list_table("source_channels")
    await update.message.reply_text("📋 المصادر:\n" + ("\n".join(lst) if lst else "لا يوجد"))

@admin_only
async def filter_on_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_setting("filter_enabled", True)
    await update.message.reply_text("✅ تم تفعيل الفلترة.")

@admin_only
async def filter_off_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_setting("filter_enabled", False)
    await update.message.reply_text("🚫 تم إيقاف الفلترة.")

@admin_only
async def add_allowed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /add_allowed كلمة1,كلمة2")
        return
    words = " ".join(context.args).split(",")
    for w in words:
        add_to_table("allowed_keywords", w.strip().lower())
    await update.message.reply_text("✅ تم إضافة الكلمات المسموحة.")

@admin_only
async def remove_allowed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /remove_allowed كلمة")
        return
    remove_from_table_generic("allowed_keywords", context.args[0].lower())
    await update.message.reply_text("✅ تم الحذف.")

@admin_only
async def add_blocked_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /add_blocked كلمة1,كلمة2")
        return
    words = " ".join(context.args).split(",")
    for w in words:
        add_to_table("blocked_keywords", w.strip().lower())
    await update.message.reply_text("✅ تم إضافة الكلمات الممنوعة.")

@admin_only
async def remove_blocked_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /remove_blocked كلمة")
        return
    remove_from_table_generic("blocked_keywords", context.args[0].lower())
    await update.message.reply_text("✅ تم الحذف.")

@admin_only
async def set_media_types_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /set_media_types نص,صورة,فيديو,...")
        return
    items = " ".join(context.args).split(",")
    items = [i.strip() for i in items if i.strip()]
    set_setting("media_types", items)
    await update.message.reply_text(f"✅ تم تحديث أنواع الوسائط: {', '.join(items)}")

@admin_only
async def add_ignore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /add_ignore <source>")
        return
    add_to_table("ignored_sources", context.args[0])
    await update.message.reply_text("✅ تم استثناء المصدر.")

@admin_only
async def remove_ignore_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /remove_ignore <source>")
        return
    remove_from_table_generic("ignored_sources", context.args[0])
    await update.message.reply_text("✅ تمت الإزالة.")

@admin_only
async def add_always_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /add_always <source>")
        return
    add_to_table("always_send_sources", context.args[0])
    await update.message.reply_text("✅ تم إضافة المصدر للقائمة الإجبارية.")

@admin_only
async def remove_always_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /remove_always <source>")
        return
    remove_from_table_generic("always_send_sources", context.args[0])
    await update.message.reply_text("✅ تمت الإزالة.")

@admin_only
async def filter_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_setting("target_group")
    enabled = get_setting("filter_enabled")
    media = get_setting("media_types") or []
    allowed = get_list_table("allowed_keywords")
    blocked = get_list_table("blocked_keywords")
    ignored = get_list_table("ignored_sources")
    always = get_list_table("always_send_sources")
    text = (
        f"📊 حالة الفلترة:\n"
        f"- المجموعة الهدف: {target}\n"
        f"- مفعل: {'✅' if enabled else '❌'}\n"
        f"- الوسائط المسموح بها: {', '.join(media) if media else 'الكل'}\n"
        f"- الكلمات المسموحة: {', '.join(allowed) if allowed else 'لا يوجد'}\n"
        f"- الكلمات الممنوعة: {', '.join(blocked) if blocked else 'لا يوجد'}\n"
        f"- القنوات المستثناة: {', '.join(ignored) if ignored else 'لا يوجد'}\n"
        f"- القنوات الإجبارية: {', '.join(always) if always else 'لا يوجد'}\n"
    )
    await update.message.reply_text(text)

# ---------- forwarder runtime management ----------
running_forwarders = {}  # name -> task

async def run_forwarder(name):
    rec = get_session_db(name)
    if not rec:
        print("No session:", name)
        return
    api_id, api_hash, session_str = rec
    client = TelegramClient(StringSession(session_str), api_id, api_hash)

    @client.on(events.NewMessage)
    async def on_new(event):
        try:
            # حصلنا الإعدادات من DB
            target = get_setting("target_group")
            if not target:
                return

            filter_enabled = get_setting("filter_enabled")
            media_types = get_setting("media_types") or []
            allowed = [w.lower() for w in get_list_table("allowed_keywords")]
            blocked = [w.lower() for w in get_list_table("blocked_keywords")]
            ignored = get_list_table("ignored_sources")
            always = get_list_table("always_send_sources")
            sources = get_list_table("source_channels")

            # معلومات الرسالة
            chat = await event.get_chat()
            source_name = getattr(chat, "username", None) or str(chat.id)

            # إن لم تكن هذه المصدر ضمن قائمة المصادر المراقبة -> تجاهل
            if sources and source_name not in sources:
                return

            # استثناء القنوات
            if source_name in ignored:
                return

            # فحص التكرار
            msg_key = f"{event.chat_id}_{event.id}"
            if has_sent(msg_key):
                return

            # نوع الميديا
            text = (event.raw_text or "").lower()
            media_type = "نص"
            if event.photo:
                media_type = "صورة"
            elif event.video:
                media_type = "فيديو"
            elif event.audio or event.voice:
                media_type = "صوت"
            elif event.document:
                media_type = "ملف"

            always_flag = source_name in always

            # فلترة
            if filter_enabled and not always_flag:
                # blocked
                if any(b in text for b in blocked):
                    return
                # allowed
                if allowed and not any(a in text for a in allowed):
                    return
                # media types
                if media_types and media_type not in media_types:
                    return

            # إعادة التوجيه مع التعامل مع FloodWait
            try:
                await client.forward_messages(int(target), event.message)
                mark_sent(msg_key)
                # تأخير بسيط لتقليل الضغط
                await asyncio.sleep(1)
            except errors.FloodWaitError as e:
                print(f"FloodWait: wait {e.seconds}s")
                await asyncio.sleep(e.seconds + 1)
                # بعد الانتظار نحاول مرة ثانية
                try:
                    await client.forward_messages(int(target), event.message)
                    mark_sent(msg_key)
                except Exception as ex2:
                    print("Forward retry failed:", ex2)

        except Exception as e:
            print("Handler error:", e)

    await client.start()
    print("Forwarder started for session:", name)
    try:
        await client.run_until_disconnected()
    finally:
        await client.disconnect()
        print("Forwarder stopped for session:", name)

@admin_only
async def start_forwarder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /start_forwarder <session_name>")
        return
    name = context.args[0]
    if name in running_forwarders:
        await update.message.reply_text("⚠️ هذا الـ forwarder يعمل بالفعل.")
        return
    task = asyncio.create_task(run_forwarder(name))
    running_forwarders[name] = task
    await update.message.reply_text(f"▶️ تم تشغيل forwarder للجلسة `{name}`")

@admin_only
async def stop_forwarder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ استخدم: /stop_forwarder <session_name>")
        return
    name = context.args[0]
    task = running_forwarders.get(name)
    if not task:
        await update.message.reply_text("ℹ️ لا يوجد forwarder يعمل بهذا الاسم.")
        return
    task.cancel()
    running_forwarders.pop(name, None)
    await update.message.reply_text(f"⏹️ تم إيقاف forwarder `{name}`")

@admin_only
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    running = ", ".join(running_forwarders.keys()) or "لا شيء"
    sent_count = cur.execute("SELECT COUNT(*) FROM sent_messages").fetchone()[0]
    await update.message.reply_text(f"📡 الحالة:\n- Forwarders شغالة: {running}\n- الرسائل المرسلة: {sent_count}")

# ---------- تشغيل البوت ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # تسجيل أوامر
    app.add_handler(CommandHandler("start_setup", start_setup))
    app.add_handler(CommandHandler("set_api", set_api))
    app.add_handler(CommandHandler("set_phone", set_phone))
    app.add_handler(CommandHandler("enter_code", enter_code))
    app.add_handler(CommandHandler("enter_pass", enter_pass))
    app.add_handler(CommandHandler("sessions", sessions_list))
    app.add_handler(CommandHandler("del_session", sessions_delete))

    app.add_handler(CommandHandler("set_target", set_target))
    app.add_handler(CommandHandler("add_source", add_source_cmd))
    app.add_handler(CommandHandler("remove_source", remove_source_cmd))
    app.add_handler(CommandHandler("list_sources", list_sources_cmd))

    app.add_handler(CommandHandler("filter_on", filter_on_cmd))
    app.add_handler(CommandHandler("filter_off", filter_off_cmd))
    app.add_handler(CommandHandler("add_allowed", add_allowed_cmd))
    app.add_handler(CommandHandler("remove_allowed", remove_allowed_cmd))
    app.add_handler(CommandHandler("add_blocked", add_blocked_cmd))
    app.add_handler(CommandHandler("remove_blocked", remove_blocked_cmd))
    app.add_handler(CommandHandler("set_media_types", set_media_types_cmd))
    app.add_handler(CommandHandler("add_ignore", add_ignore_cmd))
    app.add_handler(CommandHandler("remove_ignore", remove_ignore_cmd))
    app.add_handler(CommandHandler("add_always", add_always_cmd))
    app.add_handler(CommandHandler("remove_always", remove_always_cmd))
    app.add_handler(CommandHandler("filter_status", filter_status_cmd))

    app.add_handler(CommandHandler("start_forwarder", start_forwarder_cmd))
    app.add_handler(CommandHandler("stop_forwarder", stop_forwarder_cmd))
    app.add_handler(CommandHandler("status", status_cmd))

    await app.initialize()

    try:
        # تشغيل البوت
        await app.start_polling()
    except asyncio.CancelledError:
        print("Bot has been stopped.")
    finally:
        # التوقف عن استقبال التحديثات عند إيقاف البوت
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
