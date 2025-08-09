import asyncio
from telethon import TelegramClient, events

# بيانات التوثيق
api_id = '26075519'
api_hash = '5819201f8de7de4ea548335e78a59696'
phone_number = '+249904085742'
session_name = '1BJWap1sBu4B_MI3Ons8go-nv9Fk5TAekMcl0GoG2it9aZqw7BP7ZKIpem39ZgjIj2qCMyFKVMOipqB8I0UnP_lGP839MKadaCsi9qyT8o4F7bpS6eDNoOs-x3DM1dM7eSIIxx4sJj7-dVhJ4BlsLQvnrsqNnG2pb1JjM5tIkWI0GjVWuHXevOpcXwt94nIF_I3tgTZbosbUEf9yM2767-jhOaFB2D_6snf0zP5J122IMX3uG49HX7q0HBj0Q-W2q5n-QcPGGnvaVsTtNdpg27t-YnpkfkYJwUOkLAE9rNjJwi3TPtQATDy_AX6BBWp0OrK8wHCcTt76AGvx77BimCkY5-HX4WTE='  # اسم الجلسة المحفوظة

# المعرفات الخاصة بالقنوات/المجموعات
source_channel_ids = [
    'source_channel_id1',
    'source_channel_id2',
    # أضف المزيد من القنوات هنا
]
target_chat_id = 'target_chat_id'  # المعرف الخاص بالقناة/المجموعة المستهدفة

# إنشاء العميل باستخدام الجلسة المحفوظة
client = TelegramClient(session_name, api_id, api_hash)

# قائمة لتخزين الرسائل التي تم توجيهها لمنع التكرار
forwarded_messages = set()

async def main():
    # تسجيل الدخول تلقائيًا باستخدام الجلسة المحفوظة
    await client.start(phone_number)  # سيتم التوثيق تلقائيًا إذا كانت الجلسة موجودة
    print("Logged in successfully.")

    # الحدث الذي يستمع للرسائل الجديدة من القنوات المحددة
    @client.on(events.NewMessage(chats=source_channel_ids))
    async def handler(event):
        # تحقق من أن الرسالة لم تُرسل مسبقًا (لتجنب التكرار)
        if event.message.id not in forwarded_messages:
            try:
                # إعادة توجيه الرسالة إلى القناة/المجموعة المستهدفة
                await event.forward_to(target_chat_id)
                # إضافة المعرف إلى مجموعة الرسائل المحفوظة لمنع التكرار
                forwarded_messages.add(event.message.id)
                print(f"Forwarded message: {event.message.id}")
            except Exception as e:
                print(f"Error forwarding message: {e}")
        else:
            print(f"Message {event.message.id} already forwarded, skipping.")

    # تشغيل البوت بشكل مستمر
    await client.run_until_disconnected()

# تشغيل الكود
asyncio.run(main())
