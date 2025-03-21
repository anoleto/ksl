from __future__ import annotations

import discord
import psutil

from discord.ext import commands
from datetime import datetime
from typing import TYPE_CHECKING

import config
import random
import os
import sys

if TYPE_CHECKING:
    from main import Bot

class Info(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
    
    @commands.command(
        name="info",
        description="get bot's info"
    )
    async def info(self, ctx: commands.Context) -> None:
        """get bot's info"""
        d: datetime = datetime.now() - self.bot.startup_time # delta
        h: int # hours
        m: int # minutes
        s: int # seconds
        h, remainder = divmod(int(d.total_seconds()), 3600)
        m, s = divmod(remainder, 60)

        memory_usage = psutil.Process().memory_info().rss / 1024 ** 2

        info = (
            "kselon my favorite femboy\n"
            "my old discord bot rewritten in [python](https://www.python.org/)\n\n"
            f"online for: {h}h {m}m {s}s\n"
            f"started at: <t:{int(self.bot.startup_time.timestamp())}:F>\n\n"
            f"memory usage: {memory_usage:.2f} MB\n"
        )

        cpu_usage = psutil.cpu_percent(interval=1, percpu=True)

        for i, usage in enumerate(cpu_usage, start=1):
            info += f"CPU core {i}: {usage}%\n"

        data_path = ".data"

        info += (
            f"\nservers: {len(ctx.bot.guilds)}\n"
            f"beatmaps cached: {len([file for file in os.listdir(data_path) if os.path.isfile(os.path.join(data_path, file))])}\n"
            f"bot latency: {round(self.bot.latency * 1000, 2)}ms\n"
            f"discord.py version: [{discord.__version__}](https://github.com/Rapptz/discord.py)\n"
            f"python version: [{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}](https://www.python.org/)\n"
        )

        info += "\n\n**[source code](https://github.com/anoleto/discord-bot)**\n"
        
        embed = discord.Embed(title=f"{ctx.bot.user}'s info", 
                              description=info, color=0x424549, 
                              url=random.choice(config.ownercheckmotd))
        
        embed.set_footer(text="made by anolet")
        embed.set_image(url="https://assets.ppy.sh/beatmaps/2271393/covers/cover.jpg")
        embed.set_thumbnail(url=self.bot.user.avatar)
        
        await ctx.send(embed=embed)

async def setup(bot: Bot) -> None:
    await bot.add_cog(Info(bot))