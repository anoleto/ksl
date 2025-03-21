from __future__ import annotations

import discord
import os
import osrparse

from discord.ext import commands
from typing import TYPE_CHECKING
from objects import glob
from utils.OsuMapping import Mods, osrparseMod_dict

if TYPE_CHECKING:
    from main import Bot

class Tools(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        """ Tools i might use in the future """
        self.bot: Bot = bot
        self.mods = Mods

    @commands.command(
        name="changemod",
        aliases=['cm', 'rp'],
        description="Change replay mod.",
    )
    async def changemod(self, ctx, *, mods_str: str = None):
        """ Change replay mod. hardrock handler later im schooling
            !changemod (.osr attachments) <mods>
            ex.
            !rp hdhr (with osr replay)
        """
        if len(ctx.message.attachments) == 0:
            await ctx.send("Please attach a .osr file.")
            return

        attachment = ctx.message.attachments[0]

        if not attachment.filename.endswith(".osr"):
            await ctx.send("Please attach a valid .osr file.")
            return
            
        if not mods_str:
            await ctx.send("Please specify mods to apply.")
            return

        try:
            osr_content = await attachment.read()

            with open("temp_replay.osr", "wb") as f:
                f.write(osr_content)

            with open("temp_replay.osr", "rb") as f:
                replay = osrparse.Replay.from_file(f)

            new_mods = 0
            mod_str = mods_str.lower()
            
            i = 0
            while i < len(mod_str):
                if mod_str[i].isspace():
                    i += 1
                    continue
                    
                mod_found = False
                for length in range(2, 3):
                    if i + length <= len(mod_str):
                        sub_mod = mod_str[i:i+length]
                        if sub_mod in osrparseMod_dict:
                            mod_enum = osrparseMod_dict[sub_mod]
                            new_mods |= mod_enum
                            i += length
                            mod_found = True
                            break
                
                if not mod_found:
                    await ctx.send(f"Unknown mod '{mod_str[i:i+2]}' in '{mods_str}'")
                    os.remove("temp_replay.osr")
                    return
                    
            replay.mods = new_mods

            new_filename = f"new_{attachment.filename}"
            
            with open(new_filename, 'wb') as f:
                replay.write_file(f)

            await ctx.send(f"changed mods to {mods_str.upper()} (value: {new_mods}):", file=discord.File(new_filename))
            
        except Exception as e:
            await ctx.send(f"error processing replay: {str(e)}")

        finally:
            # shoulda cached it instead of removing, anyway todo
            if os.path.exists("temp_replay.osr"):
                os.remove("temp_replay.osr")
            if 'new_filename' in locals() and os.path.exists(new_filename):
                os.remove(new_filename)

async def setup(bot: Bot) -> None:
    await bot.add_cog(Tools(bot))