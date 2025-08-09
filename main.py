from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel

# بيانات حسابك الشخصي
api_id = 'YOUR_API_ID'  # استبدل بـ API ID الخاص بك
api_hash = 'YOUR_API_HASH'  # استبدل بـ API Hash الخاص بك
phone_number = 'YOUR_PHONE_NUMBER'  # رقم هاتفك المستخدم في Telegram

# القنوات التي تريد إعادة توجيه رسائلها، يتم تحديدها باستخدام الـ ID
channel_ids = ['channel_id_1', 'channel_id_2']  # استبدل بـ معرفات القنوات التي تريدها

# القناة أو المجموعة التي تريد إعادة توجيه الرسائل إليها
target_group = 'target_group_username'  # على سبيل المثال: '@my_group'

# تخزين معرف الرسائل التي تم إعادة توجيهها (لتجنب التكرار)
forwarded_message_ids = set()

# إنشاء العميل
client = TelegramClient('session_name', api_id, api_hash)

# حدث الرسائل الجديدة
@client.on(events.NewMessage)
async def handler(event):
    # تحقق إذا كانت الرسالة من قناة موجودة في القنوات المحددة
    if isinstance(event.chat, PeerChannel) and str(event.chat.id) in channel_ids:
        # إذا كانت الرسالة قد تم إعادة توجيهها مسبقًا (منع التكرار)
        if event.message.id in forwarded_message_ids:
            print("تم تجاهل الرسالة (مكررة).")
            return
        
        # إضافة معرف الرسالة إلى قائمة الرسائل المعاد توجيهها
        forwarded_message_ids.add(event.message.id)
        
        # إعادة توجيه الرسالة إلى المجموعة المستهدفة
        await event.forward_to(target_group)
        print(f"تمت إعادة توجيه الرسالة من {event.chat.title} إلى {target_group}")

# تشغيل العميل
async def main():
    await client.start(phone_number)  # تسجيل الدخول باستخدام رقم الهاتف
    print("العميل يعمل ...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
