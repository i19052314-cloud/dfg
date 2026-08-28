from pyrogram import Client, filters
from pyrogram.types import Message
from utils import modules_help, prefix
from utils.db import db
import asyncio, io, os
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

running = False
task = None

def render_time(text, bg="#111111", fg="#FFFFFF"):
    img = Image.new("RGB", (512, 512), bg)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 150)
    except:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 150)
        except:
            font = ImageFont.load_default()
    draw.text((256, 256), text, font=font, fill=fg, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    buf.name = "avatar.jpg"
    buf.seek(0)
    return buf

async def set_avatar(client: Client):
    tz = db.get("custom.timeavatar", "timezone", "Europe/Moscow")
    bg = db.get("custom.timeavatar", "bg", "#111111")
    fg = db.get("custom.timeavatar", "fg", "#FFFFFF")
    try:
        now = datetime.now(ZoneInfo(tz)).strftime("%H:%M")
    except:
        now = datetime.now().strftime("%H:%M")
    buf = render_time(now, bg, fg)
    # сохраняем временно
    with open("/tmp/tavatar.jpg", "wb") as f:
        f.write(buf.getvalue())
    # удаляем старые аватарки
    try:
        photos = await client.get_profile_photos("me")
        if photos and len(photos) > 0:
            # удаляем все кроме текущей? оставим 0 чтобы чистить
            await client.delete_profile_photos([p.file_id for p in photos])
    except:
        pass
    try:
        await client.set_profile_photo(photo="/tmp/tavatar.jpg")
    except Exception as e:
        # FloodWait
        from pyrogram.errors import FloodWait
        if "FloodWait" in str(type(e)):
            await asyncio.sleep(e.value + 5)
    try:
        os.remove("/tmp/tavatar.jpg")
    except:
        pass

async def updater(client: Client):
    global running
    interval = int(db.get("custom.timeavatar", "interval", 60))
    while running:
        try:
            await set_avatar(client)
        except asyncio.CancelledError:
            break
        except:
            pass
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break

@Client.on_message(filters.command(["timeavatar", "tavatar", "tav"], prefix) & filters.me)
async def timeavatar_cmd(client: Client, message: Message):
    global running, task
    args = message.command[1:] if len(message.command) > 1 else []
    sub = args[0].lower() if args else ""
    if sub in ("on", "вкл", "start"):
        if running:
            await message.edit("<b>⏰ Уже включен</b>")
            return
        running = True
        task = asyncio.create_task(updater(client))
        db.set("custom.timeavatar", "enabled", True)
        await message.edit("<b>⏰ Часы на аватарке включены (каждую минуту, старая удаляется)</b>")
        return
    if sub in ("off", "выкл", "stop"):
        running = False
        if task:
            task.cancel()
            task = None
        db.set("custom.timeavatar", "enabled", False)
        await message.edit("<b>⏰ Часы выключены</b>")
        return
    # toggle
    if running:
        running = False
        if task:
            task.cancel()
            task = None
        db.set("custom.timeavatar", "enabled", False)
        await message.edit("<b>⏰ Часы выключены</b>")
    else:
        running = True
        task = asyncio.create_task(updater(client))
        db.set("custom.timeavatar", "enabled", True)
        await message.edit("<b>⏰ Часы включены\n⚠️ Старые аватарки удаляются</b>")

@Client.on_message(filters.command(["timeset", "tset"], prefix) & filters.me)
async def timeset_cmd(client: Client, message: Message):
    await message.edit("<b>⏳ Обновляю...</b>")
    await set_avatar(client)
    await message.edit("<b>✅ Аватарка обновлена</b>")

# автозапуск если включен в БД - ленивый старт на любом своем сообщении
@Client.on_message(filters.me)
async def _autostart_tavatar(client: Client, _):
    global running, task
    if running and task and not task.done():
        return
    if db.get("custom.timeavatar", "enabled", False) and not running:
        running = True
        task = asyncio.create_task(updater(client))

# также пробуем сразу через 5 сек если клиент уже есть
try:
    if db.get("custom.timeavatar", "enabled", False):
        running = True
        async def _delayed_start():
            await asyncio.sleep(5)
            # найдем клиент через pyrogram
            try:
                from pyrogram import Client as C
                # dummy - ждем что _autostart_tavatar сработает на следующем сообщении
                pass
            except:
                pass
        # не запускаем тут task без client, ждем _autostart_tavatar
        pass
except:
    pass

modules_help["timeavatar"] = {
    "timeavatar [on|off]": "Вкл/выкл часы на аватарке 19:23 каждую минуту (старая удаляется). Просто .timeavatar - toggle",
    "tavatar": "Алиас",
    "tav": "Алиас",
    "timeset": "Принудительно обновить сейчас",
}
