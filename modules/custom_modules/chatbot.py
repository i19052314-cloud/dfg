#  Modified chatbot module (Gemini) - answers everyone
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from utils import modules_help, prefix
from utils.config import gemini_key
from utils.db import db
from utils.scripts import format_exc, import_library

genai = import_library("google.genai", "google-genai")
_gemini = genai.Client(api_key=gemini_key)

_TRIGGER = (filters.mentioned | filters.reply | filters.private) & filters.text & ~filters.me


@Client.on_message(_TRIGGER)
async def chatbot(_, message: Message):
    if not db.get("core.chatbot", "enabled", True):
        return

    prompt = message.text
    if message.reply_to_message and message.reply_to_message.text:
        prompt = f"{message.reply_to_message.text}\n\nReply: {message.text}"

    try:
        await message.reply_chat_action(enums.ChatAction.TYPING)
        response = _gemini.models.generate_content(
            model="gemini-3-flash-preview", contents=prompt
        )
        await message.reply_text(response.text)
    except Exception as e:
        await message.reply_text(f"An error occurred: {format_exc(e)}")


@Client.on_message(filters.command("chatoff", prefix) & filters.me)
async def chatoff(_, message: Message):
    db.set("core.chatbot", "enabled", False)
    await message.reply_text("<b>ChatBot is off now</b>")


@Client.on_message(filters.command("chaton", prefix) & filters.me)
async def chaton(_, message: Message):
    db.set("core.chatbot", "enabled", True)
    await message.reply_text("<b>ChatBot is on now</b>")


modules_help["chatbot"] = {
    "chatoff": "Turn off AI ChatBot",
    "chaton": "Turn on AI ChatBot",
}