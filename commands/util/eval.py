from __future__ import annotations

import discord

import traceback
import textwrap
import sys
import random

from discord.ext import commands
from typing import TYPE_CHECKING

import config

if TYPE_CHECKING:
    from main import Bot

class Eval(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
    
    @commands.command(
        name="eval",
        aliases=['py'],
        description="to run python code and return it here",
    )
    async def eval_command(self, ctx: commands.Context, *, code: str) -> None:
        """a dangerous command to run python code and returns the result here"""

        if ctx.author.id != config.OwnerID:
            await ctx.send(random.choice(config.ownercheckmotd))
            return
        
        exec_namespace = {**globals(), **locals(), **{mod.__name__: mod for mod in sys.modules.values()}}

        indented_code = textwrap.indent(textwrap.dedent(code), '    ')
        wrapped_code = f"""
async def _execute():
{indented_code}
"""

        try:
            exec(wrapped_code, exec_namespace)
            result = await exec_namespace["_execute"]()
            await ctx.send(result)
        except Exception:
            await ctx.send(f"Error: {traceback.format_exc()}")

async def setup(bot: discord.Bot) -> None:
    await bot.add_cog(Eval(bot))