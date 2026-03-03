import os
import logging
import requests
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- FLASK SERVER FOR RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
# Inko Render ke 'Environment Variables' mein set karenge (Good Practice)
API_KEY = os.getenv("MEDIA_CM_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- MEDIA.CM LOGIC ---
def get_upload_server():
    url = f"https://media.cm/api/upload/server?key={API_KEY}"
    try:
        response = requests.get(url).json()
        if response.get("status") == 200:
            return response.get("result")
    except Exception as e:
        print(f"Server fetch error: {e}")
    return None

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("📥 Downloading from Telegram...")
    
    # Video ya Document dono handle karega
    file = update.message.video or update.message.document
    telegram_file = await file.get_file()
    file_path = f"temp_{file.file_id}"
    
    await telegram_file.download_to_drive(file_path)
    await msg.edit_text("📤 Uploading to Media.cm...")

    server_url = get_upload_server()
    if not server_url:
        await msg.edit_text("❌ Error: API Server not responding.")
        return

    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'key': API_KEY}
            r = requests.post(server_url, data=data, files=files).json()

        if r.get("msg") == "OK":
            file_code = r['files'][0]['filecode']
            await msg.edit_text(f"✅ **Upload Done!**\n\n🔗 Link: https://media.cm/{file_code}")
        else:
            await msg.edit_text("❌ Upload failed at Media.cm.")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# --- BOT START ---
def main():
    # Render ke liye Flask start karein
    keep_alive()
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
