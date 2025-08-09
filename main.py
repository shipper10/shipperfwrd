from telethon import TelegramClient, events
import config

# إعدادات التطبيق
client = TelegramClient('forwarder', config.API_ID, config.API_HASH)

# الكود الخاص بالبوت
@client.on(events.NewMessage())
async def forward_message(event):
    # اعادة توجيه الرسائل
    try:
        # التحقق من عدم تكرار الرسالة (اضافة شرط خاص هنا إذا أردت)
        await event.forward_to(config.TARGET_USER)
    except Exception as e:
        print(f"Error: {e}")

# بدء البوت
async def start_bot():
    await client.start()
    print("Bot is running...")

if __name__ == "__main__":
    client.loop.run_until_complete(start_bot())
