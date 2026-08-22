#  Chatbot module: DeepSeek, answers everyone
import json
import re

import aiohttp
from pyrogram import Client, enums, filters
from pyrogram.errors import (
    ChannelPrivate,
    ChatWriteForbidden,
    UserIsBlocked,
    PeerIdInvalid,
    SlowmodeWait,
)
from pyrogram.types import Message

from utils import modules_help, prefix
from utils.config import deepseek_base_url, deepseek_key, deepseek_model, owner_id, owner_name
from utils.db import db

_TRIGGER = filters.mentioned & filters.text & ~filters.me

_MAFIA_BOT_USERNAME = "truemafiablackbot"

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


async def _chat(prompt, system):
    headers = {
        "Authorization": f"Bearer {deepseek_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": deepseek_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            deepseek_base_url.rstrip("/") + "/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            raw = await resp.text()
            try:
                data = json.loads(raw)
            except (ValueError, json.JSONDecodeError):
                data = None

            if resp.status != 200 or not isinstance(data, dict):
                raise RuntimeError(_extract_error(data, raw, resp.status))

            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise RuntimeError(_extract_error(data, raw, resp.status))


def _extract_error(data, raw, status):
    """Достаёт человекочитаемую ошибку из ответа любой формы."""
    if isinstance(data, dict):
        err = data.get("error", data.get("message"))
        if isinstance(err, dict):
            msg = err.get("message") or err.get("code") or err.get("type")
            if msg:
                return str(msg)
        elif isinstance(err, str) and err:
            return err
    snippet = (raw or "").strip()
    if snippet:
        return f"HTTP {status}: {snippet[:300]}"
    return f"HTTP {status}"


@Client.on_message(_TRIGGER)
async def chatbot(client, message: Message):
    if not db.get("core.chatbot", "enabled", True):
        return
    if not deepseek_key:
        await message.reply_text(
            "<b>DEEPSEEK_KEY не задан в переменных окружения!</b>"
        )
        return

    prompt = message.text
    if message.reply_to_message and message.reply_to_message.text:
        prompt = f"{message.reply_to_message.text}\n\nReply: {message.text}"

    sender = message.from_user
    if sender and (sender.username or "").lower() == _MAFIA_BOT_USERNAME:
        return
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
        except (ChatWriteForbidden, UserIsBlocked, PeerIdInvalid, SlowmodeWait, ChannelPrivate):
            pass
        answer = await _chat(prompt, system)
        answer = re.sub(r"https?://\S+", "ссылка удалена", answer)
        await message.reply_text(answer)
    except (ChatWriteForbidden, UserIsBlocked, PeerIdInvalid, SlowmodeWait, ChannelPrivate):
        # Нельзя писать в этот чат (бан/блок/ограничение) — просто выходим
        return
    except Exception as e:
        try:
            await message.reply_text(f"An error occurred: {e}")
        except (ChatWriteForbidden, UserIsBlocked, PeerIdInvalid, SlowmodeWait, ChannelPrivate):
            return


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