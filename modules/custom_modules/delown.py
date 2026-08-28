from pyrogram import Client, filters
from pyrogram.types import Message
from utils import modules_help, prefix
from pyrogram.errors import FloodWait
import asyncio

@Client.on_message(filters.command(["delown", "dme", "clearmy"], prefix) & filters.me)
async def delown(client: Client, message: Message):
    try:
        limit = int(message.command[1]) if len(message.command) > 1 else 100
    except:
        limit = 100
    limit = min(limit, 1000)
    try:
        await message.edit(f"<b>Удаляю {limit} своих сообщений...</b>")
    except:
        try:
            await message.reply(f"<b>Удаляю {limit} своих сообщений...</b>")
        except:
            pass
    count = 0
    ids = []
    async for msg in client.get_chat_history(message.chat.id, limit=1500):
        if msg.from_user and msg.from_user.is_self:
            if message.reply_to_message and msg.id < message.reply_to_message.id:
                break
            ids.append(msg.id)
            if len(ids) >= limit:
                break
    for i in range(0, len(ids), 100):
        chunk = ids[i:i+100]
        try:
            await client.delete_messages(message.chat.id, chunk)
            count += len(chunk)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await client.delete_messages(message.chat.id, chunk)
            count += len(chunk)
        except Exception as e:
            try:
                await message.edit(f"<b>Ошибка: {e}</b>")
            except:
                try:
                    await client.send_message(message.chat.id, f"<b>Ошибка: {e}</b>")
                except:
                    pass
            return
        await asyncio.sleep(0.3)
    try:
        await client.delete_messages(message.chat.id, message.id)
    except:
        pass
    try:
        await client.send_message("me", f"Удалено {count} сообщений в чате {message.chat.id}")
    except:
        pass

modules_help["delown"] = {
    "delown [кол-во]": "Удалить свои сообщения в чате. По умолчанию 100, макс 1000. Пример: .delown 50",
    "dme [кол-во]": "Алиас",
    "clearmy [кол-во]": "Алиас. Если реплай - удаляет от реплая до конца",
}
