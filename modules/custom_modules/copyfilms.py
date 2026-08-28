from pyrogram import Client, filters
from pyrogram.types import Message
from utils import modules_help, prefix
import re

@Client.on_message(filters.command(["copyfilms", "films", "getfilms", "copyfilms_en", "films_en"], prefix) & filters.me)
async def copyfilms(client: Client, message: Message):
    # .copyfilms @channel 100 - скопировать названия фильмов из канала в Избранное
    # .copyfilms_en @channel 100 - только английские названия
    # .copyfilms 50 - из текущего чата
    args = message.command[1:]
    only_en = message.command[0].lower() in ("copyfilms_en", "films_en") or "en" in [a.lower() for a in args]
    if only_en:
        args = [a for a in args if a.lower() != "en"]
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
    link_pattern = re.compile(r"https?://t\.me/NitokinMovies4Bot\?start=[\w\-]+", re.IGNORECASE)
    try:
        async for msg in client.get_chat_history(target, limit=limit):
            text = msg.text or msg.caption or ""
            # собираем все ссылки из текста + кнопок
            found_links = []
            if text:
                found_links += link_pattern.findall(text)
                # иногда без https: t.me/NitokinMovies4Bot?start=
                found_links += re.findall(r"t\.me/NitokinMovies4Bot\?start=[\w\-]+", text, re.IGNORECASE)
                found_links = [l if l.startswith("http") else "https://" + l for l in found_links]
            # кнопки
            if msg.reply_markup and getattr(msg.reply_markup, "inline_keyboard", None):
                for row in msg.reply_markup.inline_keyboard:
                    for btn in row:
                        url = getattr(btn, "url", None)
                        if url and "NitokinMovies4Bot" in url:
                            found_links += link_pattern.findall(url)
                            if not found_links or url not in found_links:
                                if "start=" in url:
                                    found_links.append(url)
            if found_links:
                for link in found_links:
                    # нормализуем
                    if not link.startswith("http"):
                        link = "https://" + link.lstrip("/")
                    titles.append(link)
                continue
            # если ссылок нет - fallback на название
            if not text.strip():
                continue
            first = text.strip().split("\n")[0].strip()
            first = re.sub(r"^[^\wА-Яа-я]+", "", first).strip()
            if len(first) < 3 or len(first) > 120:
                continue
            if first.lower() in ("подпишись", "реклама", "подписывайся"):
                continue
            if only_en:
                if not re.search(r"[A-Za-z]", first) or re.search(r"[А-Яа-яЁё]", first):
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
    "copyfilms [@канал] [кол-во]": "Скопировать названия/ссылки из канала в Избранное. Примеры: .copyfilms @movies 100 | .copyfilms 50 | .getfilms",
    "copyfilms_en [@канал] [кол-во]": "Только английские названия",
    "films": "Алиас",
    "getfilms": "Алиас",
    "films_en": "Только англ",
}
