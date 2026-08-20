#  Manus chatbot module - answers everyone
import asyncio
import time

import aiohttp
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from utils import modules_help, prefix
from utils.config import manus_key
from utils.db import db

API = "https://api.manus.ai/v2"
MAIN_TASK = "agent-default-main_task"
POLL_INTERVAL = 5
MAX_WAIT = 240

_busy = asyncio.Lock()

_TRIGGER = (filters.mentioned | filters.reply | filters.private) & filters.text & ~filters.me


async def _api(path, payload=None):
    headers = {"x-manus-api-key": manus_key, "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        if payload is not None:
            async with session.post(API + path, headers=headers, json=payload) as resp:
                return resp.status, await resp.json()
        async with session.get(API + path, headers=headers) as resp:
            return resp.status, await resp.json()


async def _poll_answer(after_ts):
    status, data = await _api(
        f"/task.listMessages?task_id={MAIN_TASK}&order=desc&limit=5"
    )
    if status != 200:
        raise RuntimeError(data.get("error", {}).get("message", f"HTTP {status}"))
    for m in data.get("messages", []):
        mtype = m.get("type")
        if mtype == "status_update":
            agent_status = m.get("status_update", {}).get("agent_status")
            if agent_status == "error":
                raise RuntimeError("Manus task error")
        if mtype == "assistant_message" and int(m.get("timestamp", 0)) > after_ts:
            return m["assistant_message"].get("content")
    return None


@Client.on_message(_TRIGGER)
async def chatbot(_, message: Message):
    if not db.get("core.chatbot", "enabled", True):
        return
    if not manus_key:
        await message.reply_text("<b>MANUS_KEY не задан в переменных окружения!</b>")
        return

    prompt = message.text
    if message.reply_to_message and message.reply_to_message.text:
        prompt = f"{message.reply_to_message.text}\n\nReply: {message.text}"

    await message.reply_chat_action(enums.ChatAction.TYPING)
    thinking = await message.reply_text("<b>⏳ Manus думает...</b>")

    async with _busy:
        try:
            sent_ms = int(time.time() * 1000)
            status, data = await _api(
                "/task.sendMessage",
                {"task_id": MAIN_TASK, "message": {"content": prompt}},
            )
            if status != 200:
                raise RuntimeError(data.get("error", {}).get("message", f"HTTP {status}"))

            deadline = time.time() + MAX_WAIT
            while time.time() < deadline:
                await asyncio.sleep(POLL_INTERVAL)
                answer = await _poll_answer(sent_ms)
                if answer:
                    await thinking.edit_text(answer)
                    return
            await thinking.edit_text(
                "<b>Manus думал слишком долго. Попробуй ещё раз.</b>"
            )
        except Exception as e:
            await thinking.edit_text(f"<b>Ошибка:</b> {e}")


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