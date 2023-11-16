from telegram import Update
from telegram.ext import ApplicationBuilder, Updater, CommandHandler,filters, MessageHandler, CallbackContext
import requests
import os
from dotenv import load_dotenv
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
load_dotenv()

# Load environment variables (you need to set your BOT_TOKEN and VF_API_KEY in your environment)
BOT_TOKEN = os.getenv("BOT_TOKEN")
VF_API_KEY = os.getenv("VF_API_KEY")

async def interact(update: Update, context: CallbackContext, request):
    # print(update, context)
    chat_id = update.effective_chat.id
    url = f"https://general-runtime.voiceflow.com/state/user/{chat_id}/interact"
    headers = {"Authorization": VF_API_KEY}
    data = {"request": request}
    response = requests.post(url, headers=headers, json=data).json()

    for trace in response:
        if trace["type"] in ["text", "speak"]:
            print(chat_id, trace["payload"]["message"])
            await context.bot.send_message(chat_id=chat_id, text=trace["payload"]["message"])
        elif trace["type"] == "visual":
            await context.bot.send_photo(chat_id=chat_id, photo=trace["payload"]["image"])
        elif trace["type"] == "end":
            await context.bot.send_message(chat_id=chat_id, text="Conversation is over")

async def start(update: Update, context: CallbackContext):
    await interact(update, context, {"type": "launch"})

async def handle_message(update: Update, context: CallbackContext):
    await interact(update, context, {"type": "text", "payload": update.message.text})

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()
