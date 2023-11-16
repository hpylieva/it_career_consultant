from telegram import Update
from telegram.ext import ApplicationBuilder, Updater, CommandHandler,filters, MessageHandler, CallbackContext
import requests
import os
from dotenv import load_dotenv
import logging
import asyncio
import html
import logging


import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

from telegram import Update

from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ExtBot,
    TypeHandler,
)


load_dotenv()

# Define configuration constants
URL = os.getenv("WEBHOOK")
# ADMIN_CHAT_ID = 123456
PORT = 8000
# TOKEN = "123:ABC"  # nosec B105

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load environment variables (you need to set your BOT_TOKEN and VF_API_KEY in your environment)
TOKEN = os.getenv("BOT_TOKEN")
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


async def main() -> None:
    # Here we set updater to None because we want our custom webhook server to handle the updates
    # and hence we don't need an Updater instance
    application = (
        Application.builder().token(TOKEN).updater(None).build()
    )

    # register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Pass webhook settings to telegram
    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)

    # Set up webserver
    async def telegram(request: Request) -> Response:
        """Handle incoming Telegram updates by putting them into the `update_queue`"""
        await application.update_queue.put(
            Update.de_json(data=await request.json(), bot=application.bot)
        )
        return Response()

    async def health(_: Request) -> PlainTextResponse:
        """For the health endpoint, reply with a simple plain text message."""
        return PlainTextResponse(content="The bot is still running fine :)")

    starlette_app = Starlette(
        routes=[
            Route("/telegram", telegram, methods=["POST"]),
            Route("/healthcheck", health, methods=["GET"])
        ]
    )
    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=starlette_app,
            port=PORT,
            use_colors=False,
            host="127.0.0.1",
        )
    )

    # Run application and webserver together
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())