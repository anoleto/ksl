from __future__ import annotations

from utils.OsuMapping import Mode

from typing import Tuple, Optional
from discord.ext import commands
from objects import glob

class ArgParsing:
    def __init__(self) -> None:
        """for the annoying args parsing"""
        self.mode = Mode

    async def parse_args(self, ctx: commands.Context, args: str) -> Tuple[Optional[str], Optional[int]]:
        user_id = str(ctx.author.id)
        username = ""
        mode = 0

        mentioned_users = ctx.message.mentions
        mentioned_users = [user for user in mentioned_users if user.id != ctx.bot.user.id]

        if mentioned_users:  # NOTE: !pf @user
            mentioned_user = str(mentioned_users[0].id)
            try:
                result = await glob.db.fetch('select name, mode from users where id = %s', [mentioned_user])
                if result:
                    username = result['name']
                    mode = result['mode']
                else:
                    await ctx.send(f"user <@{mentioned_user}> not found in the database.")
                    return None, None
            except Exception as err:
                await ctx.send(f"error retrieving profile from database: {err}")
                return None, None
        else:
            if args:
                if args.startswith('+'):
                    parts = args[1:].split(None, 1)
                    mode = self.mode.from_string(parts[0])
                    if len(parts) > 1:
                        username = parts[1].strip()
                else:
                    parts = args.split('+')
                    if len(parts) > 1:
                        username = parts[0].strip()
                        mode = self.mode.from_string(parts[1].strip())
                    else:
                        username = args.strip()

            if not username:
                result = await glob.db.fetch('select name, mode from users where id = %s', [user_id])
                if result:
                    username = result['name']
                    mode = result['mode'] if mode == 0 else mode
                else:
                    await ctx.send("no profile set. Use `!setprofile <name> (mode)` to set a default profile.")
                    return None, None
        #log(username)
        #log(mode)
        return username, mode