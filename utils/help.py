from __future__ import annotations

import discord
import random
import config

from discord.ext import commands

class Help(commands.HelpCommand):
    """some more cleaner help command maybe?"""
    async def send_help_message(self, ctx: commands.Context, help_text: str) -> None:
        embed = discord.Embed(title="help", description=help_text, color=discord.Color.random(), url=random.choice(config.ownercheckmotd))
        embed.set_thumbnail(url=ctx.bot.user.avatar)
        await ctx.send(embed=embed)

    async def send_bot_help(self, mapping: dict) -> None:
        help_text = "here are the commands available:\n"
        
        for cog, commands in mapping.items():
            if commands:
                if cog is not None:
                    for command in commands:
                        help_text += f"`{command.name}`: {command.description}\n"
        
        if help_text == "here are the commands available:\n":
            help_text += "no commands available."

        # mode args
        help_text += (
            "\nmode args: vn!std, vn!taiko, vn!mania, vn!ctb | rx!std, rx!taiko, rx!ctb, rx!mania (only for refx) | ap!std"
            "\nargs accepts *vn* to *001* or *rx* to *002*" # TODO: fix grammar??  its 2025 now when would you fix the grammar
            )

        await self.send_help_message(self.context, help_text)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        help_text = f"**{cog.qualified_name} commands:**\n"
        for command in cog.get_commands():
            help_text += f"`{command.name}`: {command.help}\n"
        
        await self.send_help_message(self.context, help_text)

    async def send_command_help(self, command: commands.Command) -> None:
        help_text = f"**{command.name}**\n{command.help}\n"
        if command.aliases:
            help_text += f"**aliases:** {command.aliases}"
        await self.send_help_message(self.context, help_text)