#  Chatbot module: GLM-5.2 primary, Manus fallback
import asyncio
import time

import aiohttp
from pyrogram import Client, enums, filters
from pyrogram.types import Message

from utils import modules_help, prefix
from utils.config import glm_base_url, glm_key, glm_model, manus_key
from utils.db import db

MANUS_API = "https://api.manus.ai/v2"
MANUS_TASK = "agent-default-main_task"
MANUS_POLL_INTERVAL = 5
MANUS_MAX_WAIT = 240

_busy = asyncio.Lock()

_TRIGGER = (filters.mentioned | filters.reply | filters.private) & filters.text & ~filters.me


async def _glm_chat(prompt):
    headers = {"Authorization": f"Bearer {glm_key}", "Content-Type": "application/json"}
    payload = {
        "model": glm_model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2048,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(
            glm_base_url.rstrip("/") + "/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120),
        ) as resp:
            data = await resp.json()
            if resp.status != 200:
                raise RuntimeError(
                    data.get("error", {}).get("message", f"HTTP {resp.status}")
                )
            return data["choices"][0]["message"]["content"]


async def _manus_api(path, payload=None):
    headers = {"x-manus-api-key": manus_key, "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        if payload is not None:
            async with session.post(MANUS_API + path, headers=headers, json=payload) as resp:
                return resp.status, await resp.json()
        async with session.get(MANUS_API + path, headers=headers) as resp:
            return resp.status, await resp.json()


async def _manus_poll(after_ts):
    status, data = await _manus_api(
        f"/task.listMessages?task_id={MANUS_TASK}&order=desc&limit=5"
    )
    if status != 200:
        raise RuntimeError(data.get("error", {}).get("message", f"HTTP {status}"))
    for m in data.get("messages", []):
        if (
            m.get("type") == "status_update"
            and m.get("status_update", {}).get("agent_status") == "error"
        ):
            raise RuntimeError("Manus task error")
        if m.get("type") == "assistant_message" and int(m.get("timestamp", 0)) > after_ts:
            return m["assistant_message"].get("content")
    return None


async def _manus_chat(prompt):
    sent_ms = int(time.time() * 1000)
    status, data = await _manus_api(
        "/task.sendMessage", {"task_id": MANUS_TASK, "message": {"content": prompt}}
    )
    if status != 200:
        raise RuntimeError(data.get("error", {}).get("message", f"HTTP {status}"))
    deadline = time.time() + MANUS_MAX_WAIT
    while time.time() < deadline:
        await asyncio.sleep(MANUS_POLL_INTERVAL)
        answer = await _manus_poll(sent_ms)
        if answer:
            return answer
    raise TimeoutError("Manus думал слишком долго")


@Client.on_message(_TRIGGER)
async def chatbot(_, message: Message):
    if not db.get("core.chatbot", "enabled", True):
        return

    prompt = message.text
    if message.reply_to_message and message.reply_to_message.text:
        prompt = f"{message.reply_to_message.text}\n\nReply: {message.text}"

    await message.reply_chat_action(enums.ChatAction.TYPING)
    thinking = await message.reply_text("<b>⏳ Думаю...</b>")

    async with _busy:
        try:
            if glm_key:
                answer = await _glm_chat(prompt)
            elif manus_key:
                answer = await _manus_chat(prompt)
            else:
                await thinking.edit_text(
                    "<b>Ни GLM_KEY, ни MANUS_KEY не заданы в переменных окружения!</b>"
                )
                return
            await thinking.edit_text(answer)
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