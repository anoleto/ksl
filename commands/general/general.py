from __future__ import annotations

import discord
from discord.ext import commands
from typing import TYPE_CHECKING, Optional

from datetime import datetime

if TYPE_CHECKING:
    from main import Bot

class General(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
    
    @commands.command(
        name="userinfo",
        aliases=['user', 'ui'],
        description="show an user's information"
    )
    async def userinfo(self, ctx, *, user: Optional[discord.Member] = None) -> None:
        """
        shows an user's information.
        usage: !user @rieki
        """
        if user is None:
            if ctx.message.content.split()[1:]:
                id_arg = ctx.message.content.split()[1]
                if id_arg.isdigit():
                    user_id = int(id_arg)
                    user = ctx.guild.get_member(user_id)

        user = user or ctx.author
        
        roles = [role.name for role in user.roles if role.name != "@everyone"]
        roles_sorted = ", ".join(sorted(roles)) if roles else "None"
        
        embed = discord.Embed(colour=user.colour)
        
        embed.add_field(name="user id", value=user.id, inline=True)
        embed.add_field(name="nickname", value=user.nick or "None", inline=True)
        
        created_timestamp = int(user.created_at.timestamp())
        embed.add_field(
            name="joined discord",
            value=f"<t:{created_timestamp}:F>\n(<t:{created_timestamp}:R>)",
            inline=False
        )
        
        joined_timestamp = int(user.joined_at.timestamp())
        embed.add_field(
            name="joined server",
            value=f"<t:{joined_timestamp}:F>\n(<t:{joined_timestamp}:R>)",
            inline=False
        )
        
        embed.add_field(
            name=f"roles ({len(roles)})", 
            value=roles_sorted,
            inline=False
        )
        
        if user.avatar:
            name = str(user)
            if user.display_name:
                name = f"{name} | {user.display_name}"
            embed.set_author(name=name, url=user.avatar.url)
            embed.set_thumbnail(url=user.avatar.url)
        else:
            embed.set_author(name=user.name)
        
        await ctx.send(embed=embed)

    @commands.command(name='avatar', 
                      aliases=['av'], 
                      description="shows user avatar")
    async def avatar(self, ctx, user : Optional[discord.Member] = None) -> None:
        """
        get the avatar of a user.
        usage: !av @nipa
        """
        if user is None:
            if ctx.message.content.split()[1:]:
                id_arg = ctx.message.content.split()[1]
                if id_arg.isdigit():
                    user_id = int(id_arg)
                    user = ctx.guild.get_member(user_id)
        
        author = ctx.message.author

        if not user:
            user = author
            
        roles = [x.name for x in user.roles if x.name != "@everyone"]

        if not roles: roles = ["None"]
        data = f"{str(user)}'s avatar: \n"

        embed = discord.Embed(colour=user.colour)
        embed.set_author(name=data, url=user.display_avatar.url, icon_url=user.display_avatar.url)
        embed.set_image(url=user.display_avatar.url)

        await ctx.send(embed=embed)

async def setup(bot: Bot) -> None:
    await bot.add_cog(General(bot))