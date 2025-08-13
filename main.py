import os
import telebot
from flask import Flask, request

TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_TELEGRAM_BOT_TOKEN_HERE")
bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

@bot.message_handler(content_types=['document'])
def handle_mp3_document(message):
    try:
        if not message.document.file_name.lower().endswith('.mp3'):
            bot.reply_to(message, "الملف المرسل ليس بصيغة MP3")
            return

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        with open(message.document.file_name, 'wb') as f:
            f.write(downloaded_file)

        with open(message.document.file_name, 'rb') as audio_file:
            bot.send_audio(message.chat.id, audio_file, title=message.document.file_name)

        os.remove(message.document.file_name)
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ: {e}")

@server.route('/' + TOKEN, methods=['POST'])
def get_message():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=os.environ.get("WEBHOOK_URL") + TOKEN)
    return "Webhook set!", 200

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
