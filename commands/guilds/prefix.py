from __future__ import annotations

import discord
from discord.ext import commands
from typing import TYPE_CHECKING

from utils.prefixHelper import PrefixHelper    

if TYPE_CHECKING:
    from main import Bot

async def get_prefix(bot: Bot, message: discord.Message) -> str:
    """get the prefix for a specific guild"""
    if message.guild is None:
        return '!'
    
    prefix_manager = PrefixHelper()
    return await prefix_manager.get_prefix(message.guild.id)

class Prefix(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.prefixH = PrefixHelper()
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.prefixH.set_prefix(guild.id, '!')
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self.prefixH.delete_prefix(guild.id)
        
    @commands.command(name='setprefix', description="change the bot's prefix for this server")
    @commands.has_permissions(administrator=True)
    async def set_prefix(self, ctx: commands.Context, new_prefix: str) -> None:
        """
        change the bot's prefix for this server
        usage: `!setprefix <new_prefix>`
        """
        if len(new_prefix) > 3:
            await ctx.send('Prefix must be 3 characters or less!')
            return
        
        await self.prefixH.set_prefix(ctx.guild.id, new_prefix)
        await ctx.send(f'prefix has been changed to: `{new_prefix}`')
    
    @commands.command(name='prefix', description='show the current prefix for this server')
    async def show_prefix(self, ctx: commands.Context) -> None:
        """show the current prefix for this server"""
        current_prefix = await self.prefixH.get_prefix(ctx.guild.id)

        await ctx.send(f'current prefix is: `{current_prefix}`')
    
    @commands.command(name='resetprefix', description='reset the prefix to the default')
    @commands.has_permissions(administrator=True)
    async def reset_prefix(self, ctx: commands.Context) -> None:
        """reset the server's prefix to default '!'"""
        await self.prefixH.set_prefix(ctx.guild.id, '!')

        await ctx.send('prefix has been reset to: `!`')

async def setup(bot: Bot) -> None:
    await bot.add_cog(Prefix(bot))