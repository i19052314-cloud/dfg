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
    # ищем последнее сообщение с кнопками от бота (inline + reply)
    bot_msg = None
    kb = None
    is_inline = True
    async for msg in client.get_chat_history(target, limit=50):
        if msg.reply_markup:
            if getattr(msg.reply_markup, "inline_keyboard", None):
                bot_msg = msg
                kb = msg.reply_markup.inline_keyboard
                is_inline = True
                break
            if getattr(msg.reply_markup, "keyboard", None):
                bot_msg = msg
                kb = msg.reply_markup.keyboard
                is_inline = False
                break
            # фолбек по str
            if "keyboard" in str(msg.reply_markup).lower():
                bot_msg = msg
                kb = getattr(msg.reply_markup, "inline_keyboard", None) or getattr(msg.reply_markup, "keyboard", None)
                is_inline = bool(getattr(msg.reply_markup, "inline_keyboard", None))
                break
    if not bot_msg or not kb:
        try:
            await message.edit("<b>Не нашел сообщения с кнопками (проверь что бот отправил меню с кнопками в этом чате, лимит 50)</b>")
        except:
            pass
        return
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
            txt = getattr(btn, "text", str(btn) if isinstance(btn, str) else "кнопка")
            try:
                if not is_inline:
                    await client.send_message(target, txt)
                    await asyncio.sleep(1.5)
                    continue
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
    # для reply-клавы btn - строка, для inline - объект
    txt = getattr(btn, "text", str(btn) if isinstance(btn, str) else f"{r}:{c}")
    try:
        if not is_inline:
            # ReplyKeyboard - отправляем текст кнопки как сообщение
            await client.send_message(target, txt)
            await message.edit(f"<b>Отправил: {txt}</b>")
            return
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
