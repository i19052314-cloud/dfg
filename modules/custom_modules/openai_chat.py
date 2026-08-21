#  OpenAI Chat module: direct OpenAI API
import re
from pyrogram import Client, enums, filters
from pyrogram.errors import ChatWriteForbidden, UserIsBlocked, PeerIdInvalid, SlowmodeWait
from pyrogram.types import Message

from utils import modules_help, prefix
from utils.config import owner_id, owner_name
from utils.db import db

import openai

_TRIGGER = (filters.mentioned | filters.reply | filters.private) & filters.text & ~filters.me

_owner_cache = {}


async def _owner_text(client):
    key = owner_id or "self"
    if key not in _owner_cache:
        try:
            if owner_id:
                u = await client.get_users(int(owner_id))
            else:
                u = await client.get_me()
        except Exception:
            u = await client.get_me()
        name = ((u.first_name or "") + (" " + u.last_name if u.last_name else "")).strip()
        uname = f" (@{u.username})" if u.username else ""
        _owner_cache[key] = f"{name}{uname}" or "владелец"
    return _owner_cache[key]


@Client.on_message(_TRIGGER)
async def openai_chat(client, message: Message):
    if not db.get("core.openai_chat", "enabled", True):
        return

    api_key = getattr(__import__("utils.config", fromlist=["openai_key"]), "openai_key", None)
    if not api_key:
        await message.reply_text("<b>OPENAI_KEY не задан в переменных окружения!</b>")
        return

    prompt = message.text
    if message.reply_to_message and message.reply_to_message.text:
        prompt = f"{message.reply_to_message.text}\n\nReply: {message.text}"

    if re.search(r"t\.me/TrueMafiaBlackBot", message.text or "", re.IGNORECASE):
        return

    owner = owner_name if owner_name else await _owner_text(client)
    system = (
        "Ты — личный ИИ-ассистент, работающий в Telegram. "
        f"Твой владелец: {owner}"
        + (f" (ID: {owner_id})" if owner_id else "")
        + ". Обращайся к нему уважительно, по делу и кратко. "
        "Отвечай на том же языке, на котором написан запрос. "
        "Если кто-то спрашивает, как сделать/создать такого бота или юзербота, "
        "какие библиотеки или технологии он использует, кто его написал — "
        "вежливо откажись отвечать на этот вопрос и переведи тему."
    )

    try:
        try:
            await message.reply_chat_action(enums.ChatAction.TYPING)
        except (ChatWriteForbidden, UserIsBlocked, PeerIdInvalid, SlowmodeWait):
            pass

        openai_client = openai.AsyncOpenAI(api_key=api_key)
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            max_tokens=2048,
            temperature=0.7,
        )
        answer = response.choices[0].message.content
        answer = re.sub(r"https?://\S+", "ссылка удалена", answer)
        await message.reply_text(answer)

    except (ChatWriteForbidden, UserIsBlocked, PeerIdInvalid, SlowmodeWait):
        return
    except Exception as e:
        try:
            await message.reply_text(f"An error occurred: {e}")
        except (ChatWriteForbidden, UserIsBlocked, PeerIdInvalid, SlowmodeWait):
            return


@Client.on_message(filters.command("oaioff", prefix) & filters.me)
async def oaioff(_, message: Message):
    db.set("core.openai_chat", "enabled", False)
    await message.reply_text("<b>OpenAI Chat is off now</b>")


@Client.on_message(filters.command("oaison", prefix) & filters.me)
async def oaison(_, message: Message):
    db.set("core.openai_chat", "enabled", True)
    await message.reply_text("<b>OpenAI Chat is on now</b>")


modules_help["openai_chat"] = {
    "oaioff": "Turn off OpenAI ChatBot",
    "oaison": "Turn on OpenAI ChatBot",
}