import os
from pyrogram import Client, filters
import asyncio

# الحصول على المتغيرات من بيئة التشغيل (من Koyeb)
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
TARGET_GROUP = int(os.environ.get("TARGET_GROUP"))

# قائمة بقنوات المصدر
# تأكد من أن حسابك عضو في هذه القنوات
SOURCE_CHANNELS = [
    -1001234567890,  # مثال: معرف القناة الأولى
    -1009876543210,  # مثال: معرف القناة الثانية
]

# تهيئة الكلاينت (userbot)
# "my_account" هو اسم ملف الجلسة الذي سيتم إنشاؤه
app = Client(
    "my_account",
    api_id=API_ID,
    api_hash=API_HASH
)

@app.on_message(filters.chat(SOURCE_CHANNELS) & filters.incoming)
async def forward_messages(client, message):
    try:
        await message.forward(TARGET_GROUP)
    except Exception as e:
        print(f"حدث خطأ: {e}")

print("برنامج إعادة التوجيه يعمل...")

# تشغيل الكلاينت
app.run()
