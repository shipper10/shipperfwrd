from telethon import TelegramClient, events

# بيانات الجلسة
api_id = '26075519'  # قم بوضع API ID هنا
api_hash = '5819201f8de7de4ea548335e78a59696'  # قم بوضع API HASH هنا
session_name = '1BJWap1sAUH6y3Hk0PU0710Qaw8SBrrKCRMPvQnoPuMarlmk2kCJnWAOSFqASYXGOOH7hm0GetoH9u6YYhc7R34-DlaJTd0myYmo_pXuiqtx6d2KnvivgXrShibsSUAdJs1lTyRWalpvJwDR0DMSKgkOKV9k2Ioint6WcIDWTH7z5prZ4syE35t6_q6_HYtEMCyJ68MGQbHPJuwkQ30r-JsT-Vt3LxWuEgR6jpXWyDqFNYXNxeUWYm-o3NUrp32MAPDdl1JySG_bLeHGwvxFinmwyXYHOOmNQIGrpY21AzMntKJKXNAXeMbqr_LWUiNPMcxKtcDRebXAED7xdj0mlEDOEBQpP8lY='  # اسم الجلسة

# القنوات المستهدفة (تستطيع إضافة أو تعديل القنوات باستخدام المعرفات)
target_channel = '-1002686274384'  # قناة أو مجموعة الهدف

# قم بتحديد قنوات المصدر هنا
source_channels = ['-1001668684235', '-1001595923708']  # قنوات المصدر

client = TelegramClient(session_name, api_id, api_hash)

# دالة لإعادة توجيه الرسائل
@client.on(events.NewMessage(chats=source_channels))
async def handler(event):
    # تأكد من أن الرسالة ليست من البوت نفسه
    if event.sender_id != client.get_me().id:
        await client.forward_messages(target_channel, event.message)

# تشغيل العميل
async def main():
    await client.start()
    print("بوت يعمل الآن...")
    await client.run_until_disconnected()

# بدء العمل
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
