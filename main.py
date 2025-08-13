import os
import telebot
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TELEGRAM_BOT_TOKEN_HERE")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

@bot.message_handler(content_types=['document'])
def handle_mp3_document(message):
    try:
        filename = message.document.file_name
        if not filename.lower().endswith('.mp3'):
            bot.reply_to(message, "الملف المرسل ليس بصيغة MP3")
            return

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open(filename, 'wb') as f:
            f.write(downloaded_file)

        with open(filename, 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file, title=filename)

        os.remove(filename)
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")

@server.route('/' + TOKEN, methods=['POST'])
def get_message():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return "OK", 200

@server.route("/setwebhook")
def set_webhook():
    if WEBHOOK_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{WEBHOOK_URL}{TOKEN}")
        return "Webhook set!", 200
    return "WEBHOOK_URL not configured", 500

@server.route("/")
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    server.run(host="0.0.0.0", port=port)
