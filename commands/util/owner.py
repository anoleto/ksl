from __future__ import annotations

import discord
import asyncio
import os
import sys
import random
import traceback
import textwrap

from discord.ext import commands

from typing import TYPE_CHECKING
from typing import List
from typing import Dict
from typing import Optional

from datetime import datetime
from utils.logging import log, Ansi

import config

if TYPE_CHECKING:
    from main import Bot

class Owner(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.reloaded_cogs: List[str] = []
        self.command_stats: Dict[str, int] = {}
    
    async def owner_check(self, ctx: commands.Context) -> bool:
        """Check if the user is the bot owner"""
        if ctx.author.id != config.OwnerID:
            await ctx.send(random.choice(config.ownercheckmotd))
            return False
        return True
    
    @commands.command(
        name="eval",
        aliases=['py'],
        description="to run python code and return it here",
    )
    async def eval_command(self, ctx: commands.Context, *, code: str) -> None:
        """a dangerous command to run python code and returns the result here"""
        if not await self.owner_check(ctx):
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
    
    @commands.command(
        name="shutdown", 
        aliases=["stop"],
        
    )
    async def shutdown(self, ctx: commands.Context) -> None:
        """shuts down the bot"""
        if not await self.owner_check(ctx):
            return
            
        log(f"shutdown command used by {ctx.author}", Ansi.YELLOW)
        await ctx.send("shutting down...")
        await self.bot.close()
    
    async def _reload_single_cog(self, cog_path: str) -> tuple[bool, Optional[Exception]]:
        try:
            await self.bot.reload_extension(cog_path)
            self.reloaded_cogs.append(cog_path)
            log(f"reloaded cog: {cog_path}", Ansi.GREEN)
            return True, None
        except Exception as e:
            log(f"failed to reload {cog_path}: {e}", Ansi.RED)
            return False, e
    
    @commands.command(
        name="reload"
    )
    async def reload(self, ctx: commands.Context, cog: str = None) -> None:
        """reloads a cog or all cogs if none specified"""
        if not await self.owner_check(ctx):
            return
            
        self.reloaded_cogs = []
        
        if cog:
            success, error = await self._reload_single_cog(cog)
            if success:
                await ctx.send(f"reloaded: `{cog}`")
            else:
                await ctx.send(f"failed to reload: `{cog}`\n```py\n{error}```")
        else:
            from commands import CATEGORIES
            success_count = 0
            error_count = 0
            error_list = []
            
            for category in CATEGORIES:
                category_path = f'./commands/{category}'
                if os.path.isdir(category_path):
                    for filename in os.listdir(category_path):
                        if filename.endswith('.py') and not filename.startswith('__'):
                            extension_path = f'commands.{category}.{filename[:-3]}'
                            success, error = await self._reload_single_cog(extension_path)
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                error_list.append(f"{extension_path}: {error}")
            
            await ctx.send(f"reloaded {success_count} cogs. {error_count} errors.")
            if error_count > 0 and error_count <= 5:
                await ctx.send(f"errors:\n```py\n{chr(10).join(error_list[:5])}```")
    
    @commands.command(
        name="load"
    )
    async def load(self, ctx: commands.Context, cog: str) -> None:
        """load a new cog"""
        if not await self.owner_check(ctx):
            return
            
        try:
            await self.bot.load_extension(cog)
            await ctx.send(f"loaded: `{cog}`")
            log(f"loaded cog: {cog}", Ansi.GREEN)
            self.command_stats[cog] = 0  # init command usage tracking
        except Exception as e:
            await ctx.send(f"failed to load: `{cog}`")
            log(f"failed to load {cog}: {e}", Ansi.RED)
            traceback.print_exc()
    
    @commands.command(
        name="unload"
    )
    async def unload(self, ctx: commands.Context, cog: str) -> None:
        """Unload a cog"""
        if not await self.owner_check(ctx):
            return
            
        try:
            await self.bot.unload_extension(cog)
            await ctx.send(f"unloaded: `{cog}`")
            log(f"unloaded cog: {cog}", Ansi.GREEN)
        except Exception as e:
            await ctx.send(f"failed to unload: `{cog}`")
            log(f"failed to unload {cog}: {e}", Ansi.RED)
            traceback.print_exc()
    
    @commands.command(
        name="guilds"
    )
    async def list_guilds(self, ctx: commands.Context) -> None:
        """lists all guilds the bot is in"""
        if not await self.owner_check(ctx):
            return
            
        guilds = [f"{guild.name} (ID: {guild.id}, Members: {guild.member_count})" for guild in self.bot.guilds]
        formatted_guilds = "\n".join(guilds)
        
        if len(formatted_guilds) > 1990:
            chunks = [guilds[i:i+20] for i in range(0, len(guilds), 20)]
            for i, chunk in enumerate(chunks):
                await ctx.send(f"**guilds (Page {i+1}/{len(chunks)}):**\n```{chr(10).join(chunk)}```")
        else:
            await ctx.send(f"**guilds:**\n```{formatted_guilds}```")
    
    @commands.command(
        name="leave_guild"
    )
    async def leave_guild(self, ctx: commands.Context, guild_id: int) -> None:
        """leave a specific guild by ID"""
        if not await self.owner_check(ctx):
            return
            
        guild = self.bot.get_guild(guild_id)
        if guild:
            await ctx.send(f"leaving guild: {guild.name} (ID: {guild_id})")
            await guild.leave()
            log(f"left guild: {guild.name} (ID: {guild_id})", Ansi.YELLOW)
        else:
            await ctx.send(f"could not find guild with ID: {guild_id}")

async def setup(bot: discord.Bot) -> None:
    await bot.add_cog(Owner(bot))