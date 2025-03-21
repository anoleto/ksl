from __future__ import annotations

import discord
from discord.ext import commands
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Bot

class Ping(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
    
    @commands.command(
        name="ping",
        description="check the bot's latency"
    )
    async def ping(self, ctx: commands.Context) -> None:
        """check the bot's latency"""
        latency: float = round(self.bot.latency * 1000, 2)
        await ctx.send(f'pong! latency: {latency}ms')

async def setup(bot: Bot) -> None:
    await bot.add_cog(Ping(bot))