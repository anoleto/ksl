from __future__ import annotations

from discord.ext import commands
import discord
import httpx
import asyncio
import time
import random

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Any, Optional, Set

if TYPE_CHECKING:
    from main import Bot

@dataclass
class State:
    current_word: str
    scores: Dict[int, int]
    end_time: float
    game_message: discord.Message
    used_words: set[str]

class WordBomb(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.active_games: Dict[int, State] = {}
        self.cached_words: Set[str] = set()
        self.word_cache_task = None
        self.english_word_cache: Set[str] = set()

    async def cog_load(self) -> None:
        self.word_cache_task = asyncio.create_task(self._initialize_word_cache())

    async def cog_unload(self) -> None:
        if self.word_cache_task:
            self.word_cache_task.cancel()

    async def _initialize_word_cache(self) -> None:
        common_words = [
            "time", "play", "game", "word", "make", "like", "just", "know", "take",
            "people", "year", "good", "some", "them", "see", "other", "than", "then",
            "look", "only", "come", "over", "think", "also", "back", "after", "work",
            "first", "well", "even", "want", "give", "most", "find"
        ]
        self.cached_words.update(word.lower() for word in common_words)

    async def _is_english_word(self, word: str) -> bool:
        if word.lower() in self.english_word_cache:
            return True

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f'https://api.dictionaryapi.dev/api/v2/entries/en/{word}',
                    timeout=2.0
                )
                if response.status_code == 200:
                    self.english_word_cache.add(word.lower())
                    return True
                return False
            except (httpx.RequestError, asyncio.TimeoutError):
                return False

    async def _get_random_word(self) -> str:
        if self.cached_words:
            return random.choice(list(self.cached_words))

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    'https://random-word-api.herokuapp.com/word?lang=es',
                    timeout=2.0
                )
                word = response.json()[0]
                if await self._is_english_word(word):
                    return word
                return "game"
            except:
                return "game"

    async def _update_game_status(self, ctx: commands.Context, game_state: State) -> None:
        remaining_time = int(game_state.end_time - time.time())
        status_message = (
            f'current word: **{game_state.current_word}**\n'
            f'time remaining: **{remaining_time}s**\n\n'
            f'current scores:\n'
        )

        if game_state.scores:
            status_message += '\n'.join(
                f'{ctx.guild.get_member(player).name}: {score}'
                for player, score in sorted(game_state.scores.items(), key=lambda x: x[1], reverse=True)
            )
        else:
            status_message += "no scores yet!"

        await game_state.game_message.edit(content=status_message)

    def _contains_sequence(self, target: str, word: str, min_length: int = 2) -> bool:
        target = target.lower()
        word = word.lower()

        for seq_length in range(len(target), min_length - 1, -1):
            for i in range(len(target) - seq_length + 1):
                sequence = target[i:i + seq_length]
                if sequence in word:
                    return True

        return False
    
    @commands.guild_only()
    @commands.command(name='wordbomb', 
                      aliases=['wb'], 
                      description='start a word bomb game that continues till the time runs out.')
    async def wordbomb(self, ctx: commands.Context, time_limit: int = 60):
        """
        start a word bomb game that continues till the time runs out.
        when a player wins with a valid word, that word becomes the next target.
        time limit is in seconds.

        i think this isnt even a wordbomb game, its a word race game :rofl:

        usages:
        - !wordbomb 32
        """
        guild_id = ctx.guild.id
        if guild_id in self.active_games:
            await ctx.send("there's a game already in progress in this server!")
            return

        loading_message = await ctx.send("starting game...")
        initial_word = await self._get_random_word()
        
        game_message = await ctx.send(
            f'word bomb started!\n'
            f'time limit: {time_limit} seconds\n'
            f'rules: words must contain at least 2 characters in sequence from the current word\n'
        )
        
        await loading_message.delete()

        game_state = State(
            current_word=initial_word,
            scores={},
            end_time=time.time() + time_limit,
            game_message=game_message,
            used_words=set([initial_word.lower()])
        )
        self.active_games[guild_id] = game_state

        try:
            while time.time() < game_state.end_time:
                remaining_time = int(game_state.end_time - time.time())
                if remaining_time <= 0:
                    break

                await self._update_game_status(ctx, game_state)

                def check(message: discord.Message) -> bool:
                    if (message.guild.id != guild_id or
                        message.channel != ctx.channel or 
                        message.author == self.bot.user or 
                        not message.content.strip().isalpha()):  # NOTE: only allow alphabetic characters
                        return False

                    word = message.content.lower()

                    if word in game_state.used_words:
                        return False

                    return self._contains_sequence(game_state.current_word, word, min_length=2)

                try:
                    response = await self.bot.wait_for('message', check=check, timeout=remaining_time)

                    word = response.content.lower()

                    if not await self._is_english_word(word):
                        await response.add_reaction('❌')
                        continue

                    game_state.used_words.add(word)

                    player_id = response.author.id
                    points = len(word)
                    game_state.scores[player_id] = game_state.scores.get(player_id, 0) + points

                    await response.add_reaction('✅')
                    await ctx.send(
                        f'✨ {response.author.mention} earned {points} points with "{word}"!'
                    )

                    game_state.current_word = word

                except asyncio.TimeoutError:
                    await ctx.send('times up!')
                    continue

        finally:
            sorted_scores = sorted(game_state.scores.items(), key=lambda x: x[1], reverse=True)
            final_message = "**game over!**\n\nfinal scores:\n"

            if sorted_scores:
                for i, (player_id, score) in enumerate(sorted_scores, 1):
                    player = ctx.guild.get_member(player_id)
                    medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(i, '➖')
                    final_message += f'{medal} {player.name}: {score} points\n'
            else:
                final_message += "no one scored any points! :("

            await ctx.send(final_message)
            del self.active_games[guild_id]

async def setup(bot: Bot) -> None:
    await bot.add_cog(WordBomb(bot))