from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os

# بيانات من المتغيرات البيئية
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")

# تحويل القوائم النصية إلى أرقام
SOURCE_CHATS = [int(x) for x in os.getenv("SOURCE_CHATS", "").split(",") if x.strip()]
TARGET_CHATS = [int(x) for x in os.getenv("TARGET_CHATS", "").split(",") if x.strip()]

if not SOURCE_CHATS or not TARGET_CHATS:
    raise ValueError("❌ يجب تحديد SOURCE_CHATS و TARGET_CHATS في المتغيرات البيئية.")

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def smart_forward(event):
    for target in TARGET_CHATS:
        try:
            # المحاولة الأولى: إعادة التوجيه المباشر
            await client.forward_messages(target, event.message)
            print(f"📨 تم توجيه الرسالة من {event.chat_id} إلى {target} مباشرة")
        except Exception as e:
            print(f"⚠️ فشل التوجيه المباشر إلى {target}: {e} — سيتم نسخ المحتوى")
            try:
                # إذا فشل التوجيه، نعيد رفع المحتوى
                if event.message.media:
                    await client.send_file(target, event.message.media, caption=event.message.message or "")
                else:
                    await client.send_message(target, event.message.message)
                print(f"📤 تم نسخ الرسالة من {event.chat_id} إلى {target}")
            except Exception as e2:
                print(f"❌ فشل نسخ الرسالة إلى {target}: {e2}")

print(f"✅ البوت شغال وينتظر رسائل من {SOURCE_CHATS} ليرسلها إلى {TARGET_CHATS}...")
client.start()
client.run_until_disconnected()
