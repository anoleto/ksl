from __future__ import annotations

import discord
import config
import os
import httpx
import asyncio

from pathlib import Path
from discord.ext import commands
from typing import TYPE_CHECKING, List, Dict, Optional, Literal, NamedTuple, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from commands.osu.OsuApi.api import ApiClient

from utils.logging import log, Ansi
from utils.OsuMapping import Mode, grade_emojis
from utils.args import ArgParsing

from usecases.performance import calculate_performances, ScoreParams, calculate_osu_tools

if TYPE_CHECKING:
    from main import Bot

# NOTE: thanks mist for being on vc helping me rewriting this owo :D
# TODO: compare

# --- Data Classes and Types ---
@dataclass
class ScoreSession:
    pages: List[List[Dict]]
    current_page: int
    username: str
    player_id: int
    message: Optional[discord.Message]
    last_interaction: datetime
    command_type: Literal["recent", "top"]
    
    @property
    def is_expired(self) -> bool:
        return (datetime.now() - self.last_interaction) > timedelta(minutes=1)

class MapCalculation(NamedTuple):
    pp: float
    stars: float
    pp_if_fc: float
    #pp_bancho: float

# --- Helper Functions ---
class ScoreUtils:
    @staticmethod
    def fmt_score_details(score: Dict, beatmap: Dict, calc: MapCalculation) -> Dict[str, str]:
        """format score details into readable strings."""
        fcstr = f" ({calc.pp_if_fc}pp if FC)" if round(score['pp'], 2) != calc.pp_if_fc else ""
        modstr = "+"
        cheatvalue = None

        # XXX: remove DT if theres NC
        modstr += score['mods_readable'].replace('DT', '') if 'NC' in score['mods_readable'] else score['mods_readable']

        # NOTE: scorev2 shouldnt have cheatvalue since they are playing on stable
        if 'V2' not in modstr:
            if score['mode'] > 3:
                cheatvalue = (
                    f"▸ AC: {score['aim_value'] if score['aim'] > 0 else 'Not used'} "
                    f"▸ AR Changer: {score['ar_value'] if score['arc'] > 0 else 'Not used'} "
                    f"▸ HD Remover: {'Yes' if score['hdr'] > 0 else 'Not used'}\n"
                    f"▸ Timewarp: {score['twval'] if score['tw'] > 0 else 'Not used'} "
                    f"▸ CS Changer: {'Yes' if score['cs'] > 0 else 'Not used'}"
                )
            else:
                cheatvalue = (
                    f"▸ AC: {score['aim_value'] if score['aim'] > 0 else 'Not used'} "
                    f"▸ AR Changer: {score['ar_value'] if score['arc'] > 0 else 'Not used'} "
                    f"▸ HD Remover: {'Yes' if score['hdr'] > 0 else 'Not used'}"
                )

        # play_time
        unix_playtime = datetime.fromisoformat(score['play_time']).timestamp()

        return {
            'title': f"{beatmap['artist']} - {beatmap['title']} [{beatmap['version']}]",
            'pp_display': f"{round(score['pp'], 2)}pp{fcstr}", # (bancho: {calc.pp_bancho}pp)
            'accuracy': f"{float(score['acc']):.2f}%",
            'combo': f"{score['max_combo']}x/{beatmap['max_combo']}x",
            'hits': f"[{score['n300']}/{score['n100']}/{score['n50']}/{score['nmiss']}]",
            'score_display': f"{score['score']:,}",
            'mods': modstr,
            'stars': f"{calc.stars}★",
            'cheatval': cheatvalue if cheatvalue is not None else "",
            'scoreset': f"<t:{int(unix_playtime)}:R>"
        }

    @staticmethod
    def create_pages(scores: List[Dict], page_size: int = 1) -> List[List[Dict]]:
        """Split scores into pages."""
        return [scores[i:i + page_size] for i in range(0, len(scores), page_size)]

# --- Map Calculator ---
# NOTE: move this somewhere?
class BeatmapCalculator:
    CACHE_DIR = Path(".data")

    def __init__(self):
        self.CACHE_DIR.mkdir(exist_ok=True)

    async def download_map(self, beatmap_id: int, beatmap_md5: str) -> str:
        """download and cache beatmap file."""
        filepath = self.CACHE_DIR / f"{beatmap_md5}.osu"
        
        if not filepath.exists():
            async with httpx.AsyncClient() as client:
                response = await client.get(f"https://osu.ppy.sh/osu/{beatmap_id}")
                if response.status_code != 200:
                    raise Exception(f"Failed to download beatmap with id {beatmap_id}")
                filepath.write_bytes(response.content)

        return str(filepath)

    async def calculate_map_stats(self, score: Dict, beatmap: Dict) -> MapCalculation:
        """calculate map statistics if fc including PP and stars."""
        beatmap_path = await self.download_map(beatmap['id'], beatmap['md5'])
        
        score_params = ScoreParams(
            mode=score['mode'],
            mods=score['mods'],
            combo=beatmap['max_combo'],
            nmiss=0,
            acc=score['acc'],

            # NOTE: for refx
            AC=score['aim_value'],
            AR=score['ar_value'],
            TW=score['twval'],
            CS=score['cs'],
            HD=score['hdr']
        )
        
        calc = calculate_performances(beatmap_path, [score_params])[0]
        #bancho_calc = calculate_osu_tools(beatmap_path, [score_params], "/home/ano/discord-bot/osu-tools")[0] # god..
        
        return MapCalculation(
            pp=round(score['pp'], 2),
            stars=round(float(calc['difficulty']['stars']), 2),
            pp_if_fc=round(calc['performance']['pp'], 2),
            #pp_bancho=round(bancho_calc['performance']['pp'], 2)
        )

# --- Score Embed ---
class ScoreEmbed:
    def __init__(self, server: str):
        self.server = server
        self.calculator = BeatmapCalculator()

    async def create_single_score_embed(self, score: Dict, username: str, player_id: int) -> discord.Embed:
        """recent command."""
        beatmap = score['beatmap']
        calc = await self.calculator.calculate_map_stats(score, beatmap)
        details = ScoreUtils.fmt_score_details(score, beatmap, calc)
        scoreset = f"▸ score set: {details['scoreset']}\n" if score['grade'] != 'F' else ''
        
        embed = discord.Embed(
            description=(
                f"▸ {grade_emojis.get(score['grade'], score['grade'])} "
                f"▸ **{details['pp_display']}** ▸ {details['accuracy']}\n"
                f"▸ {details['score_display']} ▸ {details['combo']} ▸ {details['hits']}\n"
                f"{scoreset}"
                f"{details['cheatval']} " # NOTE: only for refx
            ),
            color=0x2ECC71 if score['grade'] != 'F' else 0xE74C3C
        )
        
        if score['grade'] != 'F':
            embed.description += f"▸ [Replay](https://api.{self.server}/v1/get_play?id={score['id']})" # NOTE: should be get_replay if not refx
        
        embed.set_author(
            name=f"{details['title']} {details['mods']} [{details['stars']}]",
            icon_url=f"https://a.{self.server}/{player_id}",
            url=f"https://osu.ppy.sh/b/{beatmap['id']}"
        )
        embed.set_image(url=f"https://assets.ppy.sh/beatmaps/{beatmap['set_id']}/covers/cover.jpg")
        embed.set_footer(text=f"on {self.server}")
        
        return embed

    async def create_multi_score_embed(
        self,
        scores: List[Dict],
        username: str,
        player_id: int,
        current_page: int,
        total_pages: int
    ) -> discord.Embed:
        """top command."""
        embed = discord.Embed(title=f"Top plays for {username}", color=0x2ECC71)
        
        for i, score in enumerate(scores, 1):
            beatmap = score['beatmap']
            calc = await self.calculator.calculate_map_stats(score, beatmap)
            details = ScoreUtils.fmt_score_details(score, beatmap, calc)
            scoreset = f"▸ score set: {details['scoreset']}\n" if score['grade'] != 'F' else ''
            
            value = (
                f"▸ {grade_emojis.get(score['grade'], score['grade'])} "
                f"▸ **{details['pp_display']}** ▸ {details['accuracy']}\n"
                f"▸ {details['score_display']} ▸ {details['combo']} ▸ {details['hits']}\n"
                f"▸ {details['mods']} ▸ {details['stars']}\n"
                f"{scoreset}"
                f"{details['cheatval']}" # NOTE: only for refx
                f" ▸ [Replay](https://api.{self.server}/v1/get_play?id={score['id']})" # NOTE: should be get_replay if not refx
            )
            
            embed.add_field(
                name=f"{i + (current_page * 5)}. {details['title']}",
                value=value,
                inline=False
            )

        embed.set_footer(text=f"Page {current_page + 1}/{total_pages} | on {self.server}")
        embed.set_thumbnail(url=f"https://a.{self.server}/{player_id}")
        
        return embed

# --- Score Paginator ---
class ScorePaginator(discord.ui.View):
    def __init__(self, cog: Score, message_id: int):
        super().__init__(timeout=60)
        self.cog = cog
        self.message_id = message_id

    @discord.ui.button(label="←", style=discord.ButtonStyle.gray)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_pagination(interaction, "previous")

    @discord.ui.button(label="→", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_pagination(interaction, "next")

    async def handle_pagination(self, interaction: discord.Interaction, direction: str):
        session = self.cog.sessions.get(self.message_id)
        if not session:
            return

        if direction == "previous":
            session.current_page = max(0, session.current_page - 1)
        else:
            session.current_page = min(len(session.pages) - 1, session.current_page + 1)
        
        session.last_interaction = datetime.now()
        
        try:
            if session.command_type == "top":
                embed = await self.cog.embed_creator.create_multi_score_embed(
                    session.pages[session.current_page],
                    session.username,
                    session.player_id,
                    session.current_page,
                    len(session.pages)
                )
            else:
                embed = await self.cog.embed_creator.create_single_score_embed(
                    session.pages[session.current_page][0],
                    session.username,
                    session.player_id
                )
                
            await interaction.response.edit_message(embed=embed)
        except Exception as e:
            log(f"error in pagination: {e}", Ansi.YELLOW)
            await interaction.response.send_message("an error occurred while updating the scores.", ephemeral=True)

    async def on_timeout(self):
        session = self.cog.sessions.get(self.message_id)
        if session and session.message:
            try:
                await session.message.edit(view=None)
            except discord.NotFound:
                pass
            self.cog.sessions.pop(self.message_id, None)

# --- Main Score Cog ---
class Score(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot
        self.api = ApiClient()
        self.server = config.Bancho
        self.mode = Mode
        self.arg = ArgParsing
        self.sessions: Dict[int, ScoreSession] = {}
        self.embed_creator = ScoreEmbed(self.server)
        self.player_id: Optional[int] = None
        
        self.cleanup_task = bot.loop.create_task(self._cleanup_sessions())

    def cog_unload(self):
        self.cleanup_task.cancel()

    async def _cleanup_sessions(self):
        while True:
            try:
                await asyncio.sleep(60)
                expired_sessions = [
                    message_id for message_id, session in self.sessions.items()
                    if session.is_expired
                ]
                
                for message_id in expired_sessions:
                    session = self.sessions.pop(message_id)
                    if session.message:
                        try:
                            await session.message.edit(view=None)
                        except discord.NotFound:
                            pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                log(f"error in session cleanup: {e}", Ansi.YELLOW)

    async def _handle_score_command(
        self,
        ctx: commands.Context,
        args: str,
        command_type: Literal["recent", "best"],
        page_size: int
    ) -> None:
        """handle both recent and top score commands."""
        username, mode = await self.arg.parse_args(self, ctx, args)
        if username is None or mode is None:
            return

        try:
            response = await self.api.get_player_scores(command_type, username=username, mode_arg=mode)
            if response['status'] != 'success':
                await ctx.send("failed to fetch scores.")
                return

            scores = response['scores']
            if not scores:
                await ctx.send(f"no {command_type} scores found.")
                return

            self.player_id = response['player']['id']

            pages = ScoreUtils.create_pages(scores, page_size)
            
            if command_type == "best":
                embed = await self.embed_creator.create_multi_score_embed(
                    pages[0], username, self.player_id, 0, len(pages)
                )
            else:
                embed = await self.embed_creator.create_single_score_embed(
                    pages[0][0], username, self.player_id
                )

            message = await ctx.send(
                f"{command_type.title()} score{'s' if command_type == 'best' else ''} for {response['player']['name']}:",
                embed=embed
            )
            
            view = ScorePaginator(self, message.id)
            await message.edit(view=view)

            self.sessions[message.id] = ScoreSession(
                pages=pages,
                current_page=0,
                username=username,
                player_id=self.player_id,
                message=message,
                last_interaction=datetime.now(),
                command_type="top" if command_type == "best" else "recent"
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404: # XXX: might be wrong username?
                await ctx.send(f"{username} not found in {self.server}")

        except Exception as er:
            await ctx.send(f"failed to fetch scores: {er}")

    @commands.command(name="recent", aliases=['r', 'rs'], 
                      description="get player's most recent scores")
    async def recent(self, ctx: commands.Context, *, args: str = None) -> None:
        """get player's most recent scores.
        command usage example: 
        - `!r ano +rx!std`
        - `!r @rieki +vn!ctb`
        - `!r +vn!std`
        """
        await self._handle_score_command(ctx, args, "recent", 1)

    @commands.command(name="top", aliases=['t', 'osutop'],
                      description="get player's top scores")
    async def top(self, ctx: commands.Context, *, args: str = None) -> None:
        """get player's top scores.
        command usage example: 
        - `!t ano +ap!std`
        - `!t +rx!std`
        - `!t @nipa +vn!std`
        """
        await self._handle_score_command(ctx, args, "best", 5)

async def setup(bot: Bot) -> None:
    await bot.add_cog(Score(bot))