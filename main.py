import os
from telethon import TelegramClient, events

# الحصول على المتغيرات من بيئة التشغيل (من Koyeb)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
TARGET_GROUP = int(os.environ.get("TARGET_GROUP"))

# قائمة بقنوات المصدر (تأكد من أن حسابك عضو فيها)
SOURCE_CHANNELS = [
    -1001668684235,  # مثال: معرف القناة الأولى
    -1001595923708,  # مثال: معرف القناة الثانية
]

# تهيئة الكلاينت مع ملف الجلسة الثابت
# "my_account" هو اسم ملف الجلسة الذي قمت بإنشائه
client = TelegramClient('my_account', API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHANNELS))
async def forward_handler(event):
    try:
        await client.forward_messages(TARGET_GROUP, event.message)
    except Exception as e:
        print(f"حدث خطأ أثناء إعادة التوجيه: {e}")

print("برنامج إعادة التوجيه يعمل باستخدام Telethon...")

# تشغيل الكلاينت
client.start()
client.run_until_disconnected()
