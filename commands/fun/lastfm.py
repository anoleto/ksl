from __future__ import annotations

import discord
from discord.ext import commands

import httpx
import datetime
import math
import datetime

from typing import TYPE_CHECKING, Optional, Dict, List
from config import lastfm
from utils.logging import log, Ansi
from objects import glob

if TYPE_CHECKING:
    from main import Bot

class LastFM(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.api_key = lastfm
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True
        )
        
    async def cog_unload(self) -> None:
        await self.http_client.aclose()
        
    async def fetch_lastfm_data(self, username: str) -> Optional[dict]:
        params = {
            'method': 'user.getrecenttracks',
            'user': username,
            'api_key': self.api_key,
            'format': 'json',
        }
        
        try:
            response = await self.http_client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log(f"error fetching LastFM data: {e}", Ansi.YELLOW)
            return None
        
    async def fetch_user_info(self, username: str) -> Optional[dict]:
        params = {
            'method': 'user.getinfo',
            'user': username,
            'api_key': self.api_key,
            'format': 'json'
        }
        
        try:
            response = await self.http_client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log(f"error fetching LastFM user info: {e}", Ansi.YELLOW)
            return None

    @commands.command(name="nowplaying", aliases=["np", "lastfm"], description='show the currently playing track from LastFM')
    async def now_playing(self, ctx: commands.Context, username: str = None) -> None:
        """show the currently playing track from LastFM
        usage: !nowplaying
        """
        if not username:
            from_db = await glob.db.fetch('select username from lastfm where id = %s', [str(ctx.author.id)])
            if not from_db:
                await ctx.send("you must provide an username!, to set lastfm username: `!setlastfm <username>`")
                return
            
            username = from_db['username']

        data = await self.fetch_lastfm_data(username)
        user = await self.fetch_user_info(username)

        if not data or 'recenttracks' not in data or not data['recenttracks']['track']:
            await ctx.send(f"couldn't find any recent tracks for user: {username}")
            return
            
        tracks = data['recenttracks']['track']
        
        paginator = SongPaginator(tracks, username, user)
        
        message = await ctx.send(embed=paginator.get_embed(), view=paginator)
        paginator.message = message
        SongPaginator.active_sessions[username] = message

    @commands.command(name="setlastfm", description="set lastfm profile")
    async def set_lastfm(self, ctx: commands.Context, username: str = None) -> None:
        """set lastFM profile"""
        if not username:
            await ctx.send("you must provide an username!")
            return
        
        user_id = str(ctx.author.id)
        hi = await glob.db.fetch('select * from lastfm where id = %s', [user_id])

        if hi:
            await glob.db.execute(
                'update lastfm set id = %s, username = %s where id = %s',
                [user_id, username, user_id]
            )
        else:
            await glob.db.execute(
                'insert into lastfm (id, username) values (%s, %s)',
                [user_id, username]
            )

        await ctx.send(f"profile set for {username}!")

class SongPaginator(discord.ui.View):
    active_sessions: Dict[int, discord.Message] = {}
    
    def __init__(self, tracks: List[dict], username: str, user_info: str):
        super().__init__(timeout=60)
        self.tracks = tracks
        self.username = username
        self.current_page = 0
        self.tracks_per_page = 1
        self.total_pages = math.ceil(len(tracks) / self.tracks_per_page)
        self.message: Optional[discord.Message] = None
        self.userinfo = user_info
        
        if self.total_pages <= 1:
            self.first_page.disabled = True
            self.prev_page.disabled = True
            self.next_page.disabled = True
            self.last_page.disabled = True
        else:
            self.last_page.disabled = False

        self.first_page.disabled = True
        self.prev_page.disabled = True

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        
        if self.message:
            try:
                await self.message.edit(view=self)
            except:
                pass
            
            if self.username in self.active_sessions:
                del self.active_sessions[self.username]

    def get_embed(self) -> discord.Embed:
        track = self.tracks[self.current_page]

        now_playing = '@attr' in track and track['@attr'].get('nowplaying') == 'true'
        total_scrobbles = self.userinfo.get('user', {}).get('playcount', 'unknown') if self.userinfo else 'unknown'
        
        embed = discord.Embed(
            title="Now Playing" if now_playing else "Recent Track",
            url=f"https://www.last.fm/user/{self.username}",
            color=discord.Color.random()
        )
        
        embed.add_field(
            name="Track",
            value=f"**{track.get('name', 'Unknown')}**",
            inline=False
        )
        embed.add_field(
            name="Artist",
            value=track.get('artist', {}).get('#text', 'Unknown'),
            inline=True
        )
        embed.add_field(
            name="Album",
            value=track.get('album', {}).get('#text', 'Unknown'),
            inline=True
        )
        
        if not now_playing and 'date' in track:
            timestamp = int(track['date']['uts'])
            time_str = f"<t:{timestamp}:R>"
            embed.add_field(name="Played", value=time_str, inline=True)
        
        if 'image' in track:
            for img in track['image']:
                if img['size'] == 'large':
                    embed.set_thumbnail(url=img['#text'])
                    break
        
        embed.set_footer(text=f"Track {self.current_page + 1}/{self.total_pages} • {self.username} | total scrobbles {total_scrobbles}")
        return embed

    @discord.ui.button(label="≪", style=discord.ButtonStyle.grey)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        self.update_button_states()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="←", style=discord.ButtonStyle.grey)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_button_states()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="→", style=discord.ButtonStyle.grey)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_button_states()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="≫", style=discord.ButtonStyle.grey)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages - 1
        self.update_button_states()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    def update_button_states(self):
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == self.total_pages - 1
        self.last_page.disabled = self.current_page == self.total_pages - 1
    
async def setup(bot: Bot) -> None:
    await bot.add_cog(LastFM(bot))