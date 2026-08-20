#  Mafia game module for @TrueMafiaBlackBot
import random
import re

from pyrogram import Client, filters

from utils import modules_help, prefix

MAFIA_BOT = "TrueMafiaBlackBot"
MAFIA_START = "G_LTEwMDM3ODAwNzc1NzFfSTEyNzUy"
MAFIA_GROUP = -1003780077571
MAFIA_JOIN_RE = re.compile(
    r"(участв|участие|в игру|будете играть|хочешь сыграть|присоединиться|вступаешь|"
    r"принять участие|желаешь играть|начинаем игру|набор|поехали|играть)", re.IGNORECASE
)
MAFIA_PHASE_RE = re.compile(
    r"(голосован|выберите|ваш голос|за кого|выгоняем|день|ночь|мафия|убит|выбыл|"
    r"просыпается|ваш ход)", re.IGNORECASE
)


def _buttons(message):
    buttons = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for b in row:
                buttons.append((b.text or "", b.callback_data or b.url or ""))
    return buttons


@Client.on_message(filters.command("mafia", prefix) & filters.me)
async def mafia_join(client, message):
    await client.send_message(MAFIA_BOT, f"/start {MAFIA_START}")
    await message.delete()


@Client.on_message(filters.chat(MAFIA_GROUP) & filters.user(MAFIA_BOT))
async def mafia_game(client, message):
    text = message.text or message.caption or ""
    btns = _buttons(message)

    for bt, data in btns:
        if MAFIA_JOIN_RE.search(bt):
            try:
                await message.click(bt)
            except Exception:
                await client.request_callback_answer(message.id, data)
            return

    if btns and MAFIA_PHASE_RE.search(text):
        bt, data = random.choice(btns)
        try:
            await message.click(bt)
        except Exception:
            await client.request_callback_answer(message.id, data)
        return

    if text or btns:
        await client.send_message(
            "me",
            f"[Mafia] {message.chat.title}:\n{text}\nBTN: {btns}",
        )


modules_help["mafia"] = {
    "mafia": "Join/start mafia game in owner group",
}