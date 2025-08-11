from telethon import TelegramClient, events
import asyncio
import os
import time

# إعدادات الاتصال
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION")  # string session
SOURCES = ["source_channel_1", "source_channel_2"]  # مصادر
DESTS = ["destination_channel_1", "destination_channel_2"]  # وجهات

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

# تخزين مؤقت للألبومات
album_buffer = {}

async def send_album(dest, messages, protected, chat_username):
    files = []
    captions = []
    for m in sorted(messages, key=lambda x: x.id):
        if m.photo or m.video or m.document:
            files.append(await m.download_media())
        if m.message:
            captions.append(m.message)
    
    caption_text = captions[0] if captions else ""
    if protected:
        source_link = f"https://t.me/{chat_username}/{messages[0].id}"
        if caption_text:
            caption_text += f"\n\n[📎 المصدر]({source_link})"
        else:
            caption_text = f"[📎 المصدر]({source_link})"
    
    await client.send_file(dest, files, caption=caption_text, parse_mode="markdown")

@client.on(events.NewMessage(chats=SOURCES))
async def handler(event):
    msg = event.message
    chat = await event.get_chat()
    protected = getattr(msg, "protected_content", False)
    gid = getattr(msg, "grouped_id", None)

    # إذا كان ألبوم
    if gid:
        if gid not in album_buffer:
            album_buffer[gid] = []
        album_buffer[gid].append(msg)

        # تأخير بسيط لانتظار باقي الألبوم
        await asyncio.sleep(1)
        # إذا اكتمل الألبوم (تقديرياً)
        if len(album_buffer[gid]) >= 2:  # أقل ألبوم = صورتين
            messages = album_buffer.pop(gid)
            for dest in DESTS:
                if protected:
                    await send_album(dest, messages, True, chat.username)
                else:
                    await client.forward_messages(dest, messages)
    else:
        # رسالة فردية
        for dest in DESTS:
            if protected:
                await send_album(dest, [msg], True, chat.username)
            else:
                await client.forward_messages(dest, msg)

print("Bot is running...")
client.start()
client.run_until_disconnected()
