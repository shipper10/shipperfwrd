import os
import telebot
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

if not TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable is not set")

bot = telebot.TeleBot(TOKEN, threaded=False)
server = Flask(__name__)

@bot.message_handler(content_types=['document'])
def handle_mp3_document(message):
    try:
        filename = message.document.file_name
        if not filename.lower().endswith('.mp3'):
            bot.reply_to(message, "⚠️ الملف المرسل ليس بصيغة MP3")
            return

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        temp_path = os.path.join('/tmp', filename)
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file)

        with open(temp_path, 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file)

        os.remove(temp_path)
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ أثناء المعالجة: {e}")

@server.route(f'/{TOKEN}', methods=['POST'])
def webhook_handler():
    try:
        update = telebot.types.Update.de_json(request.get_data(as_text=True))
        bot.process_new_updates([update])
    except Exception as e:
        return str(e), 400
    return "OK", 200

@server.route("/setwebhook")
def set_webhook():
    bot.remove_webhook()
    webhook_full_url = f"{WEBHOOK_URL}{TOKEN}"
    success = bot.set_webhook(url=webhook_full_url)
    if success:
        return f"✅ Webhook set to {webhook_full_url}", 200
    return "❌ Failed to set webhook", 500

@server.route("/")
def index():
    return "✅ Bot is running and healthy!", 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    server.run(host="0.0.0.0", port=port, threaded=False)
