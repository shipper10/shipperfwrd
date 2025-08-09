import os
import asyncio
from telethon import TelegramClient, events

# تأكد من إنشاء مجلد للجلسة في المسار الذي تعمل فيه
session_dir = 'sessions'
os.makedirs(session_dir, exist_ok=True)
session_name = os.path.join(session_dir, 'my_session')

# بيانات التوثيق
api_id = '26075519'
api_hash = '5819201f8de7de4ea548335e78a59696'
phone_number = '+249904085742'

# المعرفات الخاصة بالقنوات/المجموعات
source_channel_ids = [
    '-1001595923708',
    '-1001668684235',
]
target_chat_id = '-1002686274384'

# إنشاء العميل باستخدام الجلسة المحفوظة
client = TelegramClient(session_name, api_id, api_hash)

async def main():
    await client.start(phone_number)  # سيتم التوثيق تلقائيًا إذا كانت الجلسة موجودة
    print("Logged in successfully.")

    # الحدث الذي يستمع للرسائل الجديدة من القنوات المحددة
    @client.on(events.NewMessage(chats=source_channel_ids))
    async def handler(event):
        # تحقق من أن الرسالة لم تُرسل مسبقًا
        if event.message.id not in forwarded_messages:
            try:
                # إعادة توجيه الرسالة إلى القناة/المجموعة المستهدفة
                await event.forward_to(target_chat_id)
                # إضافة المعرف إلى مجموعة الرسائل المحفوظة
                forwarded_messages.add(event.message.id)
                print(f"Forwarded message: {event.message.id}")
            except Exception as e:
                print(f"Error forwarding message: {e}")

    # تشغيل البوت بشكل مستمر
    await client.run_until_disconnected()

# تشغيل الكود
asyncio.run(main())
