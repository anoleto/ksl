from __future__ import annotations

import discord
from discord.ext import commands
import discord.ui

import httpx
import json
from typing import TYPE_CHECKING, Dict, List, Any

from utils.logging import log, Ansi
from utils.OsuMapping import Mods

if TYPE_CHECKING:
    from main import Bot

class PlayerDetailsView(discord.ui.View):
    def __init__(
        self, 
        embeds: List[discord.Embed], 
        interaction_id: int,
        player: str,
        original_data: Dict
    ):
        super().__init__()
        self.embeds = embeds
        self.interaction_id = interaction_id
        self.current_page = 0
        self.player = player
        self.original_data = original_data

        self.prev_button = discord.ui.Button(label="◀️", style=discord.ButtonStyle.secondary)
        self.next_button = discord.ui.Button(label="▶️", style=discord.ButtonStyle.secondary)
        
        self.prev_button.callback = self.previous_page
        self.next_button.callback = self.next_page
        
        self.add_item(self.prev_button)
        self.add_item(GoBackButton(interaction_id))
        self.add_item(self.next_button)

        if len(self.embeds) <= 1:
            self.prev_button.disabled = True
            self.next_button.disabled = True

    async def previous_page(self, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        await self._update_message(interaction)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self._update_message(interaction)

    async def _update_message(self, interaction: discord.Interaction):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.embeds) - 1)

        await interaction.response.edit_message(
            embed=self.embeds[self.current_page], 
            view=self
        )

class ReworkPaginationView(discord.ui.View):
    def __init__(
        self, 
        embeds: List[discord.Embed], 
        interaction_id: int, 
        data: Dict[str, Any], 
        mode: int, 
        version: int, 
        branch: int
    ):
        super().__init__()
        self.embeds = embeds
        self.interaction_id = interaction_id
        self.data = data
        self.mode = mode
        self.version = version
        self.branch = branch
        self.current_page = 0

        self.prev_button = discord.ui.Button(label="◀️", style=discord.ButtonStyle.secondary)
        self.next_button = discord.ui.Button(label="▶️", style=discord.ButtonStyle.secondary)
        
        self.prev_button.callback = self.previous_page
        self.next_button.callback = self.next_page
        
        self.add_item(self.prev_button)
        self.add_item(PlayerDetailsButton(interaction_id))
        self.add_item(self.next_button)

        if len(self.embeds) <= 1:
            self.prev_button.disabled = True
            self.next_button.disabled = True

    async def previous_page(self, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        await self._update_message(interaction)

    async def next_page(self, interaction: discord.Interaction):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        await self._update_message(interaction)

    async def _update_message(self, interaction: discord.Interaction):
        self.prev_button.disabled = (self.current_page == 0)
        self.next_button.disabled = (self.current_page == len(self.embeds) - 1)
        
        await interaction.response.edit_message(
            embed=self.embeds[self.current_page], 
            view=self
        )

class PlayerDetailsButton(discord.ui.Button):
    def __init__(self, interaction_id: int):
        super().__init__(
            label="^", 
            style=discord.ButtonStyle.primary
        )
        self.interaction_id = interaction_id

    async def callback(self, interaction: discord.Interaction):
        modal = discord.ui.Modal(title="Player Details")
        
        username_input = discord.ui.TextInput(
            label="Username",
            placeholder="Enter the exact username from the results",
            style=discord.TextStyle.short,
            required=True
        )
        modal.add_item(username_input)
        
        async def modal_submit(modal_interaction: discord.Interaction):
            await modal_interaction.response.defer()
            
            cog = modal_interaction.client.get_cog('Rework')

            previous_result = cog.previous_results.get(self.interaction_id)

            data = previous_result['data']
            username = username_input.value.strip()

            matching_players = [
                (player, scores) for player, scores in data.items() 
                if username.lower() == player.lower()
            ]

            if not matching_players:
                await modal_interaction.followup.send(
                    f"No player found matching '{username}'.", 
                    ephemeral=True
                )
                return

            player, scores = matching_players[0]
            embeds = []
            current_embed = discord.Embed(
                title=f"Top Scores for {player}",
                description=(
                    f"Mode: {previous_result['mode']} | "
                    f"Version: {previous_result['version']} | "
                    f"Branch: {previous_result['branch']}"
                ),
                color=discord.Color.green()
            )

            for score in scores:
                score_details = (
                    f"{score['original_pp']}pp "
                    f"~ re: {score['recalculated_pp']}pp "
                    f"| ({score['difference']:.2f}pp)\n "
                    f"+{Mods.to_modstr(score['mods'])}"
                )
                
                current_embed.add_field(
                    name=score['beatmap_id'], 
                    value=score_details, 
                    inline=False
                )

                if len(current_embed.fields) >= 5:
                    embeds.append(current_embed)
                    current_embed = discord.Embed(
                        title=f"Detailed Scores for {player}",
                        description=(
                            f"Mode: {previous_result['mode']} | "
                            f"Version: {previous_result['version']} | "
                            f"Branch: {previous_result['branch']}"
                        ),
                        color=discord.Color.green()
                    )

            if current_embed.fields:
                embeds.append(current_embed)

            view = PlayerDetailsView(
                embeds=embeds, 
                interaction_id=self.interaction_id,
                player=player,
                original_data=previous_result['data']
            )

            await modal_interaction.edit_original_response(
                embed=embeds[0],
                view=view
            )

        modal.on_submit = modal_submit

        await interaction.response.send_modal(modal)

class GoBackButton(discord.ui.Button):
    def __init__(self, interaction_id: int):
        super().__init__(
            label="-", 
            style=discord.ButtonStyle.secondary
        )
        self.interaction_id = interaction_id

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog('Rework')
        previous_result = cog.previous_results.get(self.interaction_id)

        view = ReworkPaginationView(
            embeds=previous_result['embeds'],
            interaction_id=self.interaction_id,
            data=previous_result['data'],
            mode=previous_result['mode'],
            version=previous_result['version'],
            branch=previous_result['branch']
        )

        view.current_page = 0

        await interaction.response.edit_message(
            embed=previous_result['embeds'][0],
            view=view
        )


class Rework(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.previous_results: Dict[int, Dict[str, Any]] = {}

    def summarize_player_scores(self, scores: List[Dict]) -> str:
        """Create a summary of a player's scores"""
        if not scores:
            return "No scores found"
        
        total_scores = len(scores)
        total_pp_diff = sum(score.get('difference', 0) for score in scores)
        avg_pp_diff = total_pp_diff / total_scores
        
        try:
            max_original_pp = max(scores, key=lambda x: x.get('original_pp', 0))['original_pp']
            max_recalculated_pp = max(scores, key=lambda x: x.get('recalculated_pp', 0))['recalculated_pp']
            worst_score = max(scores, key=lambda x: abs(x.get('difference', 0)))
        except ValueError:
            return "Error processing score data"
        
        summary = (
            f"#1 {max_original_pp:.2f}pp "
            f"~ #1 re: {max_recalculated_pp:.2f}pp "
            f"~ %: {total_pp_diff:.2f}pp "
            f"~ ={avg_pp_diff:.2f}pp= "
            f"~ ^{worst_score.get('difference', 0):.2f}pp^ "
            f"~ (ID: {worst_score.get('beatmap_id', 'N/A')})"
        )
        return summary

    @discord.app_commands.command(name="reworks", description="Current PP reworks")
    @discord.app_commands.choices(mode=[
        discord.app_commands.Choice(name="std!01", value=0),
        discord.app_commands.Choice(name="std!02", value=4),
    ])
    @discord.app_commands.choices(version=[
        discord.app_commands.Choice(name="Vanilla Calculation", value=0),
        discord.app_commands.Choice(name="osu_2019 Calculation", value=1),
        discord.app_commands.Choice(name="osu_2019_ScoreV2 Calculation", value=2),
    ])
    @discord.app_commands.choices(branch=[
        discord.app_commands.Choice(name="deployed-pp (current)", value=0),
        discord.app_commands.Choice(name="main-with-cheats", value=1),
        discord.app_commands.Choice(name="main-without-cheats", value=2),
        discord.app_commands.Choice(name="if-servers-legit", value=3),
    ])
    async def rework(
        self, 
        interaction: discord.Interaction,
        mode: int,
        version: int, 
        branch: int,
        relax: bool = False
    ) -> None:
        """Retrieve PP reworks based on selected parameters"""
        await interaction.response.defer()

        try:
            async with httpx.AsyncClient() as client:
                # https://github.com/anoleto/ppc
                response = await client.get(
                    "http://localhost:8670/calculate_pp",
                    params={
                        "mode": mode,
                        "version": version,
                        "branch": branch,
                        "rx": str(relax).lower() # for 002
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()

                embeds, view = await self._process_rework_results(interaction, data, mode, version, branch)

                if embeds:
                    view = ReworkPaginationView(
                        embeds=embeds, 
                        interaction_id=interaction.id,
                        data=data,
                        mode=mode,
                        version=version,
                        branch=branch
                    )
                    await interaction.followup.send(
                        embed=embeds[0], 
                        view=view
                    )
                else:
                    await interaction.followup.send("No PP rework data found.")

        except Exception as e:
            log(f"Rework command error: {e}", Ansi.RED)
            await interaction.followup.send(f"An error occurred: {e}")

    async def _process_rework_results(
        self, 
        interaction: discord.Interaction, 
        data: Dict, 
        mode: int, 
        version: int, 
        branch: int
    ) -> tuple:
        """Process rework results and create embeds with pagination"""
        embeds = []
        current_embed = discord.Embed(
            title="PP Rework Results",
            description=f"Mode: {mode} | Version: {version} | Branch: {branch}",
            color=discord.Color.random()
        )

        sorted_players = sorted(
            data.items(), 
            key=lambda x: sum(score.get('recalculated_pp', 0) for score in x[1]), 
            reverse=True
        )

        for player, scores in sorted_players:
            player_summary = self.summarize_player_scores(scores)
            
            current_embed.add_field(
                name=f" - {player}", 
                value=player_summary, 
                inline=False
            )

            if len(current_embed.fields) >= 5:
                embeds.append(current_embed)
                current_embed = discord.Embed(
                    title="PP Rework Results",
                    description=f"Mode: {mode} | Version: {version} | Branch: {branch}",
                    color=discord.Color.blue()
                )

        if current_embed.fields:
            embeds.append(current_embed)

        self.previous_results[interaction.id] = {
            "data": data,
            "mode": mode,
            "version": version,
            "branch": branch,
            "embeds": embeds
        }

        view = ReworkPaginationView(
            embeds=embeds, 
            interaction_id=interaction.id,
            data=data,
            mode=mode,
            version=version,
            branch=branch
        )

        return embeds, view

async def setup(bot: Bot) -> None:
    await bot.add_cog(Rework(bot))