from pyrogram import Client, filters
from pyrogram.types import Message
from utils import modules_help, prefix
import asyncio

@Client.on_message(filters.command(["click", "tap", "clickfilms"], prefix) & filters.me)
async def click_btn(client: Client, message: Message):
    # .click - кликнуть последнюю кнопку бота в этом чате
    # .click 2 - кликнуть вторую кнопку
    # .click all - кликнуть все кнопки по очереди
    # .clickfilms - алиас
    args = message.command[1:]
    target = message.chat.id
    # ищем последнее сообщение с кнопками от бота
    bot_msg = None
    async for msg in client.get_chat_history(target, limit=20):
        if msg.reply_markup and getattr(msg.reply_markup, "inline_keyboard", None):
            # ищем кнопки с фильмами
            bot_msg = msg
            break
    if not bot_msg:
        try:
            await message.edit("<b>Не нашел сообщения с кнопками</b>")
        except:
            pass
        return
    kb = bot_msg.reply_markup.inline_keyboard
    # flat list
    flat = []
    for r, row in enumerate(kb):
        for c, btn in enumerate(row):
            flat.append((r, c, btn))
    if not flat:
        await message.edit("<b>Кнопок нет</b>")
        return
    # режим all
    if args and args[0].lower() in ("all", "все"):
        try:
            await message.edit(f"<b>Кликаю {len(flat)} кнопок...</b>")
        except:
            pass
        for r, c, btn in flat:
            txt = getattr(btn, "text", "кнопка")
            try:
                # url кнопки - просто открываем
                if getattr(btn, "url", None):
                    await client.send_message("me", f"URL кнопка: {txt} -> {btn.url}")
                    continue
                # пробуем click
                try:
                    await bot_msg.click(r, c)
                except:
                    # фолбек через callback
                    try:
                        await client.request_callback_answer(target, bot_msg.id, getattr(btn, "callback_data", ""))
                    except Exception as e:
                        await client.send_message("me", f"Не смог кликнуть {txt}: {e}")
                        continue
                await asyncio.sleep(1.5)
            except Exception as e:
                await client.send_message("me", f"Ошибка клика {txt}: {e}")
        try:
            await message.edit(f"<b>Готово, кликнул {len(flat)} кнопок</b>")
        except:
            pass
        return
    # одиночный клик по номеру
    idx = 0
    if args:
        try:
            idx = int(args[0]) - 1
            if idx < 0:
                idx = 0
            if idx >= len(flat):
                idx = len(flat) - 1
        except:
            idx = 0
    r, c, btn = flat[idx]
    txt = getattr(btn, "text", f"{r}:{c}")
    try:
        if getattr(btn, "url", None):
            await message.edit(f"<b>Кнопка URL: {btn.url}</b>\n{txt}")
            return
        try:
            await bot_msg.click(r, c)
        except:
            await client.request_callback_answer(target, bot_msg.id, getattr(btn, "callback_data", ""))
        await message.edit(f"<b>Кликнул: {txt}</b>")
    except Exception as e:
        try:
            await message.edit(f"<b>Ошибка: {e}</b>")
        except:
            pass

modules_help["clickfilms"] = {
    "click [N|all]": "Кликнуть кнопку бота в этом чате. .click 1 - первую, .click 2 - вторую, .click all - все подряд",
    "tap": "Алиас",
    "clickfilms": "Алиас",
}
