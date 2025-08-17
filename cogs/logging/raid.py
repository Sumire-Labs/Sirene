import discord
from discord.ext import commands
from typing import TYPE_CHECKING
import time
from collections import deque

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.di import container
from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

class RaidDetectionCog(commands.Cog, name="RaidDetector"):
    """Detects potential raid/spam behavior."""

    # --- Configuration for raid detection ---
    JOIN_TIME_WINDOW_SECONDS = 15
    JOIN_THRESHOLD = 5
    MESSAGE_TIME_WINDOW_SECONDS = 7
    MESSAGE_THRESHOLD = 10
    ALERT_COOLDOWN_SECONDS = 60

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.db = self.container.db
        
        self.recent_joins: dict[int, deque] = {}
        self.join_alert_cooldowns: dict[int, float] = {}
        self.recent_messages: dict[int, deque] = {}
        self.message_alert_cooldowns: dict[int, float] = {}

    async def get_log_channel_and_settings(self, guild_id: int) -> tuple[discord.TextChannel | None, bool, bool]:
        """Helper to get the log channel and raid detection status for a guild."""
        settings = await self.db.get_guild_settings(guild_id)
        if not settings:
            return None, True, True # Defaults

        channel = self.bot.get_channel(settings.log_channel_id) if settings.log_channel_id else None
        if not isinstance(channel, discord.TextChannel):
            channel = None

        return channel, settings.logging_enabled, settings.raid_detection_enabled

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Checks for rapid member joins."""
        guild_id = member.guild.id
        log_channel, logging_enabled, raid_enabled = await self.get_log_channel_and_settings(guild_id)
        
        if not logging_enabled or not raid_enabled or not log_channel:
            return
        
        current_time = time.monotonic()

        last_alert_time = self.join_alert_cooldowns.get(guild_id, 0)
        if (current_time - last_alert_time) < self.ALERT_COOLDOWN_SECONDS:
            return

        if guild_id not in self.recent_joins:
            self.recent_joins[guild_id] = deque()
        
        join_deque = self.recent_joins[guild_id]
        join_deque.append(current_time)

        while join_deque and (current_time - join_deque[0]) > self.JOIN_TIME_WINDOW_SECONDS:
            join_deque.popleft()

        if len(join_deque) >= self.JOIN_THRESHOLD:
            embed = embed_factory.warning(
                title="🚨 メンバー参加レイド検知アラート",
                description=f"**{self.JOIN_TIME_WINDOW_SECONDS}秒以内**に **{len(join_deque)}人** のメンバーが参加しました。"
            )
            embed.add_field(name="最新の参加者", value=f"{member.mention} (`{member.name}`)", inline=False)
            await log_channel.send(embed=embed)

            join_deque.clear()
            self.join_alert_cooldowns[guild_id] = current_time

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Checks for rapid messages (spam)."""
        if not message.guild or message.author.bot: return

        guild_id = message.guild.id
        log_channel, logging_enabled, raid_enabled = await self.get_log_channel_and_settings(guild_id)

        if not logging_enabled or not raid_enabled or not log_channel:
            return

        current_time = time.monotonic()

        last_alert_time = self.message_alert_cooldowns.get(guild_id, 0)
        if (current_time - last_alert_time) < self.ALERT_COOLDOWN_SECONDS:
            return

        if guild_id not in self.recent_messages:
            self.recent_messages[guild_id] = deque()

        message_deque = self.recent_messages[guild_id]
        message_deque.append(current_time)

        while message_deque and (current_time - message_deque[0]) > self.MESSAGE_TIME_WINDOW_SECONDS:
            message_deque.popleft()

        if len(message_deque) >= self.MESSAGE_THRESHOLD:
            embed = embed_factory.warning(
                title="🚨 メッセージスパム検知アラート",
                description=f"**{self.MESSAGE_TIME_WINDOW_SECONDS}秒以内**に **{len(message_deque)}件** のメッセージが投稿されました。"
            )
            embed.add_field(name="最新の投稿者", value=f"{message.author.mention} (`{message.author.name}`)", inline=False)
            embed.add_field(name="チャンネル", value=message.channel.mention, inline=False)
            await log_channel.send(embed=embed)

            message_deque.clear()
            self.message_alert_cooldowns[guild_id] = current_time

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(RaidDetectionCog(bot))
