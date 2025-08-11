from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import os
from flask import Flask
import threading
import time

# ===== إعدادات الاتصال =====
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")  # string session

# فلترة القيم الفارغة + مسافات
SOURCES = [s.strip() for s in os.environ.get("SOURCES", "").split(",") if s.strip()]
TARGET_CHATS = [t.strip() for t in os.environ.get("TARGET_CHATS", "").split(",") if t.strip()]

if not SOURCES:
    print("⚠️ لا يوجد مصادر (SOURCES) صحيحة، سيتم تجاهل استقبال الرسائل.")
if not TARGET_CHATS:
    print("⚠️ لا يوجد وجهات (TARGET_CHATS) صحيحة، لن يتم إعادة التوجيه.")

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ===== Flask Health Check =====
app = Flask(__name__)

@app.route("/")
def home():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ===== تجميع الألبومات =====
album_buffer = {}  # {grouped_id: {"messages": [], "last_time": float, "chat_username": str}}

async def send_with_source(dest, messages, chat_username):
    """إعادة رفع الميديا أو النصوص مع رابط المصدر"""
    files = []
    captions = []

    for m in sorted(messages, key=lambda x: x.id):
        if m.photo or m.video or m.document or m.audio or m.voice:
            files.append(await m.download_media())
        elif m.message:
            captions.append(m.message)

    caption_text = captions[0] if captions else ""
    source_link = f"https://t.me/{chat_username}/{messages[0].id}" if chat_username else ""
    if source_link:
        if caption_text:
            caption_text += f"\n\n[📎 المصدر]({source_link})"
        else:
            caption_text = f"[📎 المصدر]({source_link})"

    if files:
        await client.send_file(dest, files, caption=caption_text, parse_mode="markdown")
    else:
        await client.send_message(dest, caption_text, parse_mode="markdown")

async def flush_album(gid):
    if gid not in album_buffer:
        return
    data = album_buffer.pop(gid)
    messages = data["messages"]
    protected = getattr(messages[0], "protected_content", False)
    chat_username = data["chat_username"]

    for dest in TARGET_CHATS:
        if protected:
            await send_with_source(dest, messages, chat_username)
        else:
            await client.forward_messages(dest, messages)

async def album_watcher():
    while True:
        now = time.time()
        for gid in list(album_buffer.keys()):
            if now - album_buffer[gid]["last_time"] >= 3:
                await flush_album(gid)
        await asyncio.sleep(1)

@client.on(events.NewMessage(chats=SOURCES if SOURCES else None))
async def handler(event):
    msg = event.message
    chat = await event.get_chat()
    gid = getattr(msg, "grouped_id", None)
    protected = getattr(msg, "protected_content", False)

    if gid:
        if gid not in album_buffer:
            album_buffer[gid] = {"messages": [], "last_time": time.time(), "chat_username": chat.username}
        album_buffer[gid]["messages"].append(msg)
        album_buffer[gid]["last_time"] = time.time()
    else:
        for dest in TARGET_CHATS:
            if protected:
                await send_with_source(dest, [msg], chat.username)
            else:
                await client.forward_messages(dest, msg)

# ===== تشغيل البوت و Flask معاً =====
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    print("Bot is running...
