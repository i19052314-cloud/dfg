#  Moon-Userbot - modified chatbot module (Gemini)
#  Responds to @mentions, replies to the userbot's messages, and PMs.
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from utils import modules_help, prefix
from utils.config import gemini_key
from utils.db import db
from utils.scripts import format_exc, import_library, restart

genai = import_library("google.genai", "google-genai")
_gemini = genai.Client(api_key=gemini_key)

chatai_users = db.getaiusers()

_TRIGGER = (filters.mentioned | filters.reply | filters.private) & filters.text & ~filters.me


@Client.on_message(filters.command("addai", prefix) & filters.me)
async def adduser(_, message: Message):
    if len(message.command) > 1:
        user_id = message.text.split(maxsplit=1)[1]
        if user_id.isdigit():
            db.addaiuser(int(user_id))
            await message.edit_text("<b>User ID Added</b>")
            restart()
        else:
            await message.edit_text("<b>User ID is invalid.</b>")
            return
    else:
        await message.edit_text(f"<b>Usage: </b><code>{prefix}addai [user_id]</code>")


@Client.on_message(filters.command("remai", prefix) & filters.me)
async def remuser(_, message: Message):
    if len(message.command) > 1:
        user_id = message.text.split(maxsplit=1)[1]
        if user_id.isdigit():
            db.remaiuser(int(user_id))
            await message.edit_text("<b>User ID Removed</b>")
            restart()
        else:
            await message.edit_text("<b>User ID is invalid.</b>")
            return
    else:
        await message.edit_text(f"<b>Usage: </b><code>{prefix}remai [user_id]</code>")


@Client.on_message(_TRIGGER)
async def chatbot(_, message: Message):
    sender = getattr(message.from_user, "id", None)
    if sender is None or sender not in chatai_users:
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
    db.remove("core.chatbot", "chatai_users")
    await message.reply_text("<b>ChatBot is off now</b>")
    restart()


@Client.on_message(filters.command("listai", prefix) & filters.me)
async def listai(_, message: Message):
    await message.edit_text(
        f"<b>User IDs in AI ChatBot List:</b>\n <code>{chatai_users}</code>"
    )


modules_help["chatbot"] = {
    "addai [user_id]*": "Add a user to AI ChatBot List",
    "remai [user_id]*": "Remove a user from AI ChatBot List",
    "listai": "List users in AI ChatBot List",
    "chatoff": "Turn off AI ChatBot",
}