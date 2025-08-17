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
    ALERT_COOLDOWN_SECONDS = 60

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.config = self.container.config_loader.config.logging
        self.db = self.container.db
        
        # {guild_id: deque([...timestamps...])}
        self.recent_joins = {}
        # {guild_id: last_alert_timestamp}
        self.join_alert_cooldowns = {}

    async def get_log_channel_for_guild(self, guild_id: int) -> discord.TextChannel | None:
        """Helper to get the log channel for a specific guild from the DB."""
        settings = await self.db.get_guild_settings(guild_id)
        if not settings: return None
        channel_id, enabled = settings
        if not enabled or not channel_id: return None
        
        channel = self.bot.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Checks for rapid member joins."""
        if not self.config.events.raid_detection: return
        
        guild_id = member.guild.id
        current_time = time.monotonic()

        # --- Cooldown Check ---
        last_alert_time = self.join_alert_cooldowns.get(guild_id, 0)
        if (current_time - last_alert_time) < self.ALERT_COOLDOWN_SECONDS:
            return # Still in cooldown

        # --- Join Tracking ---
        if guild_id not in self.recent_joins:
            self.recent_joins[guild_id] = deque()
        
        join_deque = self.recent_joins[guild_id]
        join_deque.append(current_time)

        # Remove old timestamps
        while join_deque and (current_time - join_deque[0]) > self.JOIN_TIME_WINDOW_SECONDS:
            join_deque.popleft()

        # --- Alerting ---
        if len(join_deque) >= self.JOIN_THRESHOLD:
            log_channel = await self.get_log_channel_for_guild(guild_id)
            if not log_channel: return

            embed = embed_factory.warning(
                title="🚨 レイド検知アラート",
                description=f"**{self.JOIN_TIME_WINDOW_SECONDS}秒以内**に **{len(join_deque)}人** のメンバーが参加しました。"
            )
            embed.add_field(name="最新の参加者", value=f"{member.mention} (`{member.name}`)", inline=False)
            
            await log_channel.send(embed=embed)

            # Reset deque and set cooldown to prevent spamming alerts
            join_deque.clear()
            self.join_alert_cooldowns[guild_id] = current_time

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(RaidDetectionCog(bot))
