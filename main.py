import os
import time
import asyncio
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
album_buffer = {}
ALBUM_DELAY = 3  # ثانية واحدة

# ---- health server ----
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

# ---- helper ----
async def send_with_source(dest, messages, chat_username):
    files = []
    caption = None
    entities = None

    for m in messages:
        if m.media:
            files.append(await m.download_media())
        if m.message and not caption:
            caption = m.message
            entities = m.entities  # حفظ التنسيق

    if caption and chat_username:
        caption += f"\n\n@{chat_username}"
    elif chat_username:
        caption = f"@{chat_username}"

    await client.send_file(
        dest,
        files,
        caption=caption,
        formatting_entities=entities,
        parse_mode=None
    )

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
            captions = [m.message for m in messages if m.message]
            entities = messages[0].entities if captions else None
            if captions:
                files = [await m.download_media() for m in sorted(messages, key=lambda x: x.id) if m.media]
                await client.send_file(
                    dest,
                    files,
                    caption=captions[0],
                    formatting_entities=entities,
                    parse_mode=None
                )
            else:
                await client.forward_messages(dest, messages)

async def album_watcher():
    while True:
        now = time.time()
        to_flush = [gid for gid, data in album_buffer.items() if now - data["last_time"] >= ALBUM_DELAY]
        for gid in to_flush:
            await flush_album(gid)
        await asyncio.sleep(0.5)

# ---- telegram handlers ----
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
                if msg.media:
                    await client.send_file(
                        dest,
                        msg.media,
                        caption=msg.message or "",
                        formatting_entities=msg.entities,
                        parse_mode=None
                    )
                else:
                    await client.send_message(
                        dest,
                        msg.message or "",
                        formatting_entities=msg.entities,
                        parse_mode=None
                    )

# ---- main ----
async def main():
    await client.start()
    asyncio.create_task(start_http_server())
    asyncio.create_task(album_watcher())
    print("Telegram client started.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
