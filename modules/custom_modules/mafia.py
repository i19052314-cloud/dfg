#  Mafia game module for @TrueMafiaBlackBot
import base64
import random
import re

from pyrogram import Client, filters

from utils import modules_help, prefix
from utils.config import mafia_start, owner_id
from utils.db import db

MAFIA_BOT = "TrueMafiaBlackBot"
MAFIA_LINK_RE = re.compile(
    r"t\.me/TrueMafiaBlackBot\?start=([A-Za-z0-9_\-=]+)", re.IGNORECASE
)
MAFIA_JOIN_RE = re.compile(
    r"(участв|участие|в игру|будете играть|хочешь сыграть|присоединиться|вступаешь|"
    r"принять участие|желаешь играть|начинаем игру|набор|поехали)", re.IGNORECASE
)
MAFIA_PHASE_RE = re.compile(
    r"(голосован|выберите|ваш голос|за кого|выгоняем|просыпается|ваш ход|"
    r"выберите цель|применить способность)", re.IGNORECASE
)
MAFIA_DANGER_RE = re.compile(
    r"(выход|выйти|покинуть|меню|профиль|правила|отмена|назад|статистика)", re.IGNORECASE
)
_OWNER_FILTER = filters.user(int(owner_id)) if owner_id else filters.user(0)


def _decode_group(param):
    try:
        if param.startswith("G_"):
            raw = base64.urlsafe_b64decode(param[2:] + "==").decode()
            return int(raw.split("_")[0])
    except Exception:
        pass
    return None


def game_group():
    return db.get("custom.mafia", "group_id", None) or _decode_group(mafia_start)


def set_game_group(gid):
    db.set("custom.mafia", "group_id", gid)


def _buttons(message):
    buttons = []
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for b in row:
                buttons.append((b.text or "", b.callback_data or b.url or ""))
    return buttons


def _is_game_pm_or_group(_, __, message):
    if message.outgoing:
        return False
    fu = message.from_user
    if not fu or (fu.username or "").lower() != MAFIA_BOT.lower():
        return False
    gid = game_group()
    if message.chat.type.name == "private" or getattr(message.chat, "id", None) == gid:
        return True
    return False


def _in_game_group_only(_, __, message):
    if message.outgoing:
        return False
    gid = game_group()
    return bool(message.chat and getattr(message.chat, "id", None) == gid)


def _find_link(message):
    m = MAFIA_LINK_RE.search(message.text or "")
    if m:
        return m
    if message.reply_markup and message.reply_markup.inline_keyboard:
        for row in message.reply_markup.inline_keyboard:
            for b in row:
                if b.url:
                    m = MAFIA_LINK_RE.search(b.url)
                    if m:
                        return m
    return None


async def _click(client, message, bt, data):
    try:
        await message.click(bt)
    except Exception:
        try:
            await client.request_callback_answer(message.chat.id, message.id, data)
        except Exception:
            pass


@Client.on_message(filters.command("mafia", prefix) & filters.me)
async def mafia_join(client, message):
    await client.send_message(MAFIA_BOT, f"/start {mafia_start}")
    await message.delete()


@Client.on_message(filters.command(["mafiagroup", "mafiachat"], prefix) & filters.me)
async def mafia_set_group(client, message):
    if message.chat.type.name in ("group", "supergroup"):
        set_game_group(message.chat.id)
        await message.reply_text(
            f"<b>Игровая группа мафии установлена:</b> <code>{message.chat.id}</code>"
        )
    else:
        gid = game_group()
        await message.reply_text(
            "<b>Эта команда работает только в группе.</b>\n"
            f"<b>Текущая игровая группа:</b> <code>{gid}</code>"
        )


@Client.on_message(_OWNER_FILTER & filters.text)
async def mafia_autolink(client, message):
    gid = game_group()
    if message.chat and message.chat.id == gid:
        return
    m = MAFIA_LINK_RE.search(message.text or "")
    if m:
        await client.send_message(MAFIA_BOT, f"/start {m.group(1)}")
        gid = _decode_group(m.group(1))
        if gid:
            set_game_group(gid)
            await message.reply(f"<b>Вступаю в игру и закрепляю группу:</b> <code>{gid}</code>")
        else:
            await message.reply("<b>Вступаю в игру...</b>")


@Client.on_message(filters.create(_in_game_group_only))
async def mafia_autojoin(client, message):
    m = _find_link(message)
    if m:
        await client.send_message(MAFIA_BOT, f"/start {m.group(1)}")
        gid = _decode_group(m.group(1))
        if gid and gid != game_group():
            set_game_group(gid)


@Client.on_message(filters.create(_is_game_pm_or_group))
async def mafia_game(client, message):
    text = message.text or message.caption or ""
    btns = _buttons(message)

    for bt, data in btns:
        if MAFIA_JOIN_RE.search(bt):
            await _click(client, message, bt, data)
            return

    if btns and text and MAFIA_PHASE_RE.search(text):
        safe = [(bt, data) for bt, data in btns if not MAFIA_DANGER_RE.search(bt)]
        if safe:
            bt, data = random.choice(safe)
            await _click(client, message, bt, data)
            return

    if (text or btns) and db.get("custom.mafia", "debug", False):
        title = getattr(message.chat, "title", None) or "ЛС"
        try:
            await client.send_message(
                "me",
                f"[Mafia] {title}:\n{text}\nBTN: {btns}",
            )
        except Exception:
            pass


@Client.on_message(filters.command("mafiadebug", prefix) & filters.me)
async def mafia_debug(_, message):
    cur = db.get("custom.mafia", "debug", False)
    db.set("custom.mafia", "debug", not cur)
    state = "on" if not cur else "off"
    await message.reply_text(f"<b>Mafia debug log: {state}</b>")


modules_help["mafia"] = {
    "mafia": "Join/start mafia game",
    "mafiagroup": "Set current chat as THE mafia game group",
    "mafiadebug": "Toggle mafia event logging to Saved Messages",
}
