from pyrogram import Client, filters
from pyrogram.types import Message
from utils import modules_help, prefix
from utils.db import db
import re, asyncio

async def fetch_from_bot(client: Client, link: str):
    m = re.search(r"t\.me/([^?]+)\?start=([^\s&]+)", link)
    if not m:
        return None
    bot = m.group(1)
    payload = m.group(2)
    try:
        await client.send_message(bot, f"/start {payload}")
        await asyncio.sleep(2)
        # ждем ответ бота 5 сек
        for _ in range(5):
            await asyncio.sleep(1)
            async for msg in client.get_chat_history(bot, limit=5):
                if msg.from_user and not msg.from_user.is_self:
                    if msg.video or msg.document or msg.photo:
                        return msg
                    if msg.text and "t.me" in msg.text:
                        return msg
        return None
    except Exception as e:
        return None

@Client.on_message(filters.command(["autofilms", "autofilm", "getallfilms"], prefix) & filters.me)
async def autofilms(client: Client, message: Message):
    # .autofilms @источник @назнач 50 - скопировать все фильмы как видео в канал с антидублем
    # .autofilms @источник 50 - в Избранное ссылками (без скачки)
    args = message.command[1:]
    if not args:
        await message.edit("<b>Укажи: .autofilms @источник @назнач 50</b>")
        return
    src = None
    dest = "me"
    limit = 50
    # парсим @источник @назнач число
    at_args = [a for a in args if a.startswith("@") or a.startswith("https://t.me/")]
    num_args = [a for a in args if a.isdigit()]
    if at_args:
        src = at_args[0].replace("https://t.me/", "@")
        if len(at_args) >= 2:
            dest = at_args[1]
    if num_args:
        limit = min(int(num_args[0]), 500)
    if not src:
        src = message.chat.id
    fetch_video = dest != "me" and dest.startswith("@")
    try:
        await message.edit(f"<b>Собираю {limit} из {src} -> {dest} (видео={fetch_video})...</b>")
    except:
        pass
    link_pattern = re.compile(r"https?://t\.me/Nitokin(?:Movies|Media)\d*Bot\?start=[^\s\"'&]+", re.IGNORECASE)
    raw_pattern = re.compile(r"t\.me/Nitokin(?:Movies|Media)\d*Bot\?start=[^\s\"'&]+", re.IGNORECASE)
    links = []
    try:
        async for msg in client.get_chat_history(src, limit=limit):
            text = msg.text or msg.caption or ""
            found = []
            if text:
                found += link_pattern.findall(text)
                found += raw_pattern.findall(text)
            if msg.reply_markup and getattr(msg.reply_markup, "inline_keyboard", None):
                for row in msg.reply_markup.inline_keyboard:
                    for btn in row:
                        url = getattr(btn, "url", None)
                        if url and "Nitokin" in url:
                            found.append(url)
            if not found:
                try:
                    raw = str(msg)
                    found += link_pattern.findall(raw)
                    found += raw_pattern.findall(raw)
                except:
                    pass
            for l in found:
                if not l.startswith("http"):
                    l = "https://" + l.lstrip("/")
                l = l.split("&")[0].strip()
                if l not in links:
                    links.append(l)
    except Exception as e:
        await message.edit(f"<b>Ошибка чтения: {e}</b>")
        return
    if not links:
        await message.edit("<b>Не нашел ссылок Nitokin</b>")
        return
    # антидубль БД
    sent = db.get("custom.autofilms", "sent", [])
    sent_set = set(s.lower() for s in sent)
    new_links = [l for l in links if l.lower() not in sent_set]
    # также дедуп по payload
    uniq_payload = {}
    for l in new_links:
        m = re.search(r"start=([^\s&]+)", l)
        key = m.group(1).lower() if m else l.lower()
        if key not in uniq_payload:
            uniq_payload[key] = l
    new_links = list(uniq_payload.values())
    # реверс - от старых к новым
    new_links = new_links[::-1]
    if not new_links:
        await message.edit("<b>Все фильмы уже в БД, дублей нет</b>")
        return
    await message.edit(f"<b>Нашел {len(links)} ссылок, новых {len(new_links)} -> качаю в {dest}...</b>")
    ok = 0
    fail = 0
    for link in new_links:
        try:
            if fetch_video:
                bot_msg = await fetch_from_bot(client, link)
                if bot_msg:
                    # пересылаем видео/документ в канал
                    try:
                        await bot_msg.copy(dest)
                        ok += 1
                    except:
                        try:
                            await client.forward_messages(dest, bot_msg.chat.id, bot_msg.id)
                            ok += 1
                        except Exception as e:
                            await client.send_message("me", f"{link} - {e}")
                            fail += 1
                    sent.append(link)
                    db.set("custom.autofilms", "sent", sent)
                    await asyncio.sleep(2)
                else:
                    # fallback - шлем ссылку
                    await client.send_message(dest, link)
                    ok += 1
                    sent.append(link)
                    db.set("custom.autofilms", "sent", sent)
            else:
                await client.send_message(dest, link)
                ok += 1
                sent.append(link)
                db.set("custom.autofilms", "sent", sent)
                await asyncio.sleep(0.5)
        except Exception as e:
            if "FloodWait" in str(type(e)):
                try:
                    await asyncio.sleep(e.value)
                except:
                    await asyncio.sleep(5)
                continue
            fail += 1
        await asyncio.sleep(1)
    await message.edit(f"<b>Готово: {ok} новых, {fail} ошибок, {len(new_links)-ok-fail} пропущено -> {dest}</b>")

modules_help["autofilms"] = {
    "autofilms @ист @назнач [кол-во]": "Авто-копировать фильмы как видео в канал с БД без дублей. Пример: .autofilms @NitokinMedia23Bot @мой_канал 100",
    "autofilms @ист [кол-во]": "Только ссылки в Избранное",
    "autofilm": "Алиас",
    "getallfilms": "Алиас",
}
