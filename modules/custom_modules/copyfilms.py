from pyrogram import Client, filters
from pyrogram.types import Message
from utils import modules_help, prefix
import re

@Client.on_message(filters.command(["copyfilms", "films", "getfilms"], prefix) & filters.me)
async def copyfilms(client: Client, message: Message):
    # .copyfilms @channel 100 - скопировать названия фильмов из канала в Избранное
    # .copyfilms 50 - из текущего чата
    args = message.command[1:]
    target = message.chat.id
    limit = 100
    if args:
        if args[0].startswith("@") or args[0].startswith("https://t.me/"):
            target = args[0].replace("https://t.me/", "@")
            if len(args) > 1:
                try:
                    limit = int(args[1])
                except:
                    limit = 100
        else:
            try:
                limit = int(args[0])
            except:
                pass
            if message.reply_to_message:
                target = message.reply_to_message.forward_from_chat.id if message.reply_to_message.forward_from_chat else message.chat.id
    limit = min(limit, 1000)
    try:
        await message.edit(f"<b>Собираю {limit} сообщений из {target}...</b>")
    except:
        pass
    titles = []
    try:
        async for msg in client.get_chat_history(target, limit=limit):
            text = msg.text or msg.caption or ""
            if not text.strip():
                continue
            # берем первую строку как название, чистим
            first = text.strip().split("\n")[0].strip()
            # убираем эмодзи/префиксы типа "🎬 Название"
            first = re.sub(r"^[^\wА-Яа-я]+", "", first).strip()
            if len(first) < 3 or len(first) > 120:
                continue
            # фильтр мусор
            if first.lower() in ("подпишись", "реклама", "подписывайся"):
                continue
            titles.append(first)
    except Exception as e:
        try:
            await message.edit(f"<b>Ошибка чтения канала: {e}</b>")
        except:
            pass
        return
    if not titles:
        try:
            await message.edit("<b>Не нашел названий</b>")
        except:
            pass
        return
    # убираем дубли сохраняя порядок
    seen = set()
    uniq = []
    for t in titles:
        low = t.lower()
        if low not in seen:
            seen.add(low)
            uniq.append(t)
    uniq = uniq[::-1]  # от старых к новым
    out = "\n".join(f"{i+1}. {t}" for i, t in enumerate(uniq))
    # отправляем в Избранное
    try:
        if len(out) > 4000:
            with open("films.txt", "w", encoding="utf-8") as f:
                f.write(out)
            await client.send_document("me", "films.txt", caption=f"<b>Скопировано {len(uniq)} фильмов из {target}</b>")
            import os
            os.remove("films.txt")
        else:
            await client.send_message("me", f"<b>Фильмы из {target} ({len(uniq)} шт):</b>\n\n{out}")
        await message.edit(f"<b>Готово: {len(uniq)} названий отправлено в Избранное</b>")
    except Exception as e:
        try:
            await message.edit(f"<b>Ошибка отправки: {e}</b>")
        except:
            pass

modules_help["copyfilms"] = {
    "copyfilms [@канал] [кол-во]": "Скопировать названия фильмов из канала в Избранное. Примеры: .copyfilms @movies 100 | .copyfilms 50 | .getfilms",
    "films": "Алиас",
    "getfilms": "Алиас",
}
