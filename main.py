# main.py
import os
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

# --- health HTTP server ---
async def handle_root(request):
    # يمكنك هنا إضافة منطق فحص صحة أعمق (مثل التحقق من حالة client.connected)
    status = 200 if client.is_connected() else 503
    return web.Response(text="OK" if status == 200 else "NOT READY", status=status)

async def start_http_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_root)  # مسار بديل إن رغبت
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"HTTP health server running on port {PORT}")

# --- telegram handlers (مثال مبسّط) ---
@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def handle_message(event):
    # هنا ضع كود إعادة الإرسال/التجميع الذي تفضله
    for target in TARGET_CHATS:
        try:
            if event.message.media:
                await client.send_file(target, event.message.media, caption=event.message.message or "")
            else:
                await client.send_message(target, event.message.message or "")
        except Exception as e:
            print("Send error:", e)

# --- تشغيل متزامن ---
async def main():
    await client.start()
    # شغّل HTTP server كـ task منفصل
    asyncio.create_task(start_http_server())
    print("Telegram client started.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
