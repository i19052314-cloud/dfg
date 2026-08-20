#  Moon-Userbot - telegram userbot
#  Copyright (C) 2020-present Moon Userbot Organization
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
import random

from dulwich.refs import Ref
from pyrogram import Client, filters
from pyrogram.types import Message

from utils import gitrepo, modules_help, prefix, python_version, userbot_version


@Client.on_message(filters.command(["support", "repo"], prefix) & filters.me)
async def support(_, message: Message):
    commands_count = 0.0
    for module in modules_help:
        for _cmd in module:
            commands_count += 1

    await message.edit(
        f"<b>Userbot\n\n"
        f"Python version: {python_version}\n"
        f"Modules count: {len(modules_help) / 1}\n"
        f"Commands count: {commands_count}</b>",
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command(["version", "ver"], prefix) & filters.me)
async def version(client: Client, message: Message):
    await message.delete()

    config = gitrepo.get_config()
    try:
        remote_url = config.get((b"remote", b"origin"), b"url").decode("utf-8")
        if remote_url.endswith(".git"):
            remote_url = remote_url[:-4]
    except KeyError:
        remote_url = ""

    head_sha = gitrepo.head()
    hexsha = head_sha.decode("utf-8")
    commit_obj = gitrepo.get_object(head_sha)

    commit_time = (
        datetime.datetime.fromtimestamp(commit_obj.commit_time)
        .astimezone(datetime.timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    _, ref_path = gitrepo.refs.follow(Ref(b"HEAD"))
    if ref_path:
        active_branch = ref_path.split(b"/")[-1].decode("utf-8")
    else:
        active_branch = "detached"

    author_name = commit_obj.author.decode("utf-8").split("<")[0].strip()

    await message.reply(
        f"<b>Userbot version: {userbot_version}\n"
        + (
            f"Branch: {active_branch}\n"
            if active_branch not in ["master", "main"]
            else ""
        )
        + f"Commit: {hexsha[:7]} by {author_name}\n"
        f"Commit time: {commit_time}</b>",
    )


modules_help["support"] = {
    "support": "Information about userbot",
    "version": "Check userbot version",
}
