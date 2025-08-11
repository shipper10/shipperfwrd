from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os
import asyncio

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
STRING_SESSION = os.getenv("STRING_SESSION")

SOURCE_CHATS = [int(x) for x in os.getenv("SOURCE_CHATS", "").split(",") if x.strip()]
TARGET_CHATS = [int(x) for x in os.getenv("TARGET_CHATS", "").split(",") if x.strip()]

if not SOURCE_CHATS or not TARGET_CHATS:
    raise ValueError("❌ يجب تحديد SOURCE_CHATS و TARGET_CHATS في المتغيرات البيئية.")

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

album_buffer = {}

async def get_source_text(event):
    try:
        chat = await event.get_chat()
        chat_name = chat.title or "المصدر"
        source_link = ""

        # إذا القناة أو المجموعة عامة
        if getattr(chat, "username", None):
            source_link = f"https://t.me/{chat.username}/{event.id}"
        else:
            source_link = ""  # ما في رابط مباشر

        if source_link:
            return f"\n— من: [{chat_name}]({source_link})"
        else:
            return f"\n— من: {chat_name}"
    except:
        return "\n— من: غير معروف"

@client.on(events.NewMessage(chats=SOURCE_CHATS))
async def handle_message(event):
    grouped_id = event.message.grouped_id
    source_text = await get_source_text(event)

    if grouped_id:
        for target in TARGET_CHATS:
            key = (event.chat_id, grouped_id, target)
            album_buffer.setdefault(key, []).append(event)

            await asyncio.sleep(1.5)

            if key in album_buffer:
                events_group = album_buffer.pop(key)
                events_group.sort(key=lambda e: e.message.id)

                media_list = [ev.message.media for ev in events_group if ev.message.media]
                captions = [ev.message.message or "" for ev in events_group]
                first_caption = (captions[0] if captions else "") + source_text

                try:
                    await client.send_file(target, media_list, caption=first_caption, link_preview=False)
                    print(f"📤 تم إرسال ألبوم من {event.chat_id} إلى {target}")
                except Exception as e:
                    print(f"❌ خطأ في إرسال الألبوم: {e}")
    else:
        for target in TARGET_CHATS:
            try:
                caption = (event.message.message or "") + source_text
                if event.message.media:
                    await client.send_file(target, event.message.media, caption=caption, link_preview=False)
                else:
                    await client.send_message(target, caption, link_preview=False)
                print(f"📤 تم إرسال رسالة فردية من {event.chat_id} إلى {target}")
            except Exception as e:
                print(f"❌ فشل إرسال الرسالة إلى {target}: {e}")

print(f"✅ البوت شغال وينتظر رسائل من {SOURCE_CHATS} ليرسلها إلى {TARGET_CHATS} مع رابط المصدر...")
client.start()
client.run_until_disconnected()
