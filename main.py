import asyncio
from telethon import TelegramClient, events
from telethon.errors.rpcbaseerrors import AuthKeyError
from telethon.tl.types import PeerChannel

# بيانات API الخاصة بك
api_id = '26075519'  # قم بوضع الـ API_ID هنا
api_hash = '5819201f8de7de4ea548335e78a59696'  # قم بوضع الـ API_HASH هنا
phone_number = '+249904085742'  # رقم هاتفك
target_group_id = '+249904085742'  # قم بوضع الـ ID الخاص بالمجموعة التي تريد إعادة التوجيه إليها

# اسم الجلسة
session_name = 'session_name'

# إنشاء العميل
client = TelegramClient(session_name, api_id, api_hash)

# مجموعة لتخزين الرسائل التي تم إعادة توجيهها لتجنب التكرار
processed_messages = set()

# قائمة القنوات التي تريد إعادة التوجيه منها
channels_to_forward = [
    # ضع هنا الـ ID الخاص بالقنوات التي تريد إعادة توجيه الرسائل منها
    '-1001595923708',
    '-1001668684235',
    # يمكنك إضافة المزيد من القنوات حسب الحاجة
]

async def main():
    try:
        # التحقق مما إذا كانت الجلسة موجودة أو لا
        if not client.is_user_authorized():
            # إذا لم تكن الجلسة موجودة، أرسل طلب الكود للتحقق من الرقم
            await client.send_code_request(phone_number)
            # قم بإدخال الرمز يدويًا لتوثيق الدخول
            await client.sign_in(phone_number, input("Enter the code: "))
        else:
            # إذا كانت الجلسة موجودة بالفعل
            print("تم التوثيق بنجاح!")
        
        # تابع تلقي الرسائل من القنوات والمجموعات
        @client.on(events.NewMessage)
        async def handler(event):
            # تحقق من أن الرسالة تأتي من قناة موجودة في قائمة القنوات
            if isinstance(event.chat, PeerChannel):
                if event.chat.id in channels_to_forward:
                    # التحقق من عدم إعادة توجيه نفس الرسالة
                    if event.message.id not in processed_messages:
                        # إضافة الرسالة إلى مجموعة الرسائل المعالجة
                        processed_messages.add(event.message.id)
                        # إعادة توجيه الرسالة إلى المجموعة المحددة
                        await client.forward_messages(target_group_id, event.message)
                        print(f"تم إعادة توجيه الرسالة: {event.message.id}")
        
        # قم بتشغيل البوت بشكل مستمر
        await client.run_until_disconnected()

    except AuthKeyError as e:
        print(f"حدث خطأ في التوثيق: {e}")
    except Exception as e:
        print(f"حدث خطأ غير متوقع: {e}")

# تشغيل العميل
if __name__ == "__main__":
    asyncio.run(main())
