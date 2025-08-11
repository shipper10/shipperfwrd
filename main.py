# main.py
import os
import asyncio
import time
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")
PORT = int(os.getenv("PORT", "8080"))

SOURCE_CHATS = [int(x) for x in os.getenv("SOURCE_CHATS", "").split(",") if x.strip()]
TARGET_CHATS = [int(x) for x in os.getenv("TARGET_CHATS", "").split(",") if x.strip()]

if not SOURCE_CHATS or not TARGET_CHATS:
    raise ValueError("حدد SOURCE_CHATS و TARGET_CHATS")

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

# ====== HTTP Health Check ======
async def handle_root(request):
    status = 200 if client.is_connected() else 503
    return web.Response(text="OK" if status == 200 else "NOT READY", status=status)

async def start_http_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_root)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"HTTP health server running on port {PORT}")

# ====== Album Handling ======
album_buffer = {}  # {grouped_id: {"messages": [], "last_time": float, "chat_username": str}}

async def send_with_source(dest, messages, chat_username):
    """إعادة رفع الميديا أو النصوص مع رابط المصدر"""
    files = []
    captions = []

    for m in sorted(messages, key=lambda x: x.id):
        if m.media:
            files.append(await m.download_media())
        elif m.message:
            captions.append(m.message)

    caption_text = captions[0] if captions else ""
    source_link = f"https://t.me/{chat_username}/{messages[0].id}"
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
            # البحث عن أول كابتشن في الألبوم
            captions = [m.message for m in messages if m.message]
            if captions:
                files = [await m.download_media() for m in sorted(messages, key=lambda x: x.id) if m.media]
                await client.send_file(dest, files, caption=captions[0])
            else:
                await client.forward_messages(dest, messages)

async def album_watcher():
    while True:
        now = time.time()
        for gid in list(album_buffer.keys()):
            if now - album_buffer[gid]["last_time"] >= 1:  # مهلة 1 ثانية
                await flush_album(gid)
        await asyncio.sleep(0.5)

# ====== Telegram Event ======
@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def handle_message(event):
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

# ====== Run Bot ======
async def main():
    await client.start()
    asyncio.create_task(start_http_server())
    asyncio.create_task(album_watcher())
    print("Telegram client started.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
