#  Mafia game module for @TrueMafiaBlackBot
import re

from pyrogram import Client, filters
from pyrogram.types import Message

from utils import modules_help, prefix

MAFIA_BOT = "TrueMafiaBlackBot"
MAFIA_START = "G_LTEwMDM3ODAwNzc1NzFfSTEyNzUy"
MAFIA_GROUP = -1003780077571
MAFIA_JOIN_RE = re.compile(
    r"(участвоват|участие|в игру|будете играть|хочешь сыграть|присоединиться|вступаешь|"
    r"принять участие|желаешь играть|начинаем игру|набор)", re.IGNORECASE
)
MAFIA_ASK_YES = ("да", "участвую", "да участвую", "согласен", "я в игре")


@Client.on_message(filters.command("mafia", prefix) & filters.me)
async def mafia_join(client, message: Message):
    await client.send_message(MAFIA_BOT, f"/start {MAFIA_START}")
    await message.delete()


@Client.on_message(
    filters.chat(MAFIA_GROUP) & filters.user(MAFIA_BOT) & filters.text
)
async def mafia_game(client, message: Message):
    text = message.text
    if MAFIA_JOIN_RE.search(text):
        for reply in MAFIA_ASK_YES:
            await message.reply(reply)
            break
        return

    if re.search(r"(голосован|выберите|ваш голос|за кого|выгоняем|день|ночь)", text, re.IGNORECASE):
        await client.send_message("me", f"[Mafia] {message.chat.title}:\n{text}")


modules_help["mafia"] = {
    "mafia": "Join/start mafia game in owner group",
}