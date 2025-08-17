import discord
from discord.ext import commands
from typing import TYPE_CHECKING

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.di import container
from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

class LoggingCog(commands.Cog, name="EventLogger"):
    """Handles logging of various server events."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.config = self.container.config_loader.config.logging
        self.log_channel: discord.TextChannel | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        """Fetches the log channel once the bot is ready."""
        if self.config.channel_id != 0:
            self.log_channel = self.bot.get_channel(self.config.channel_id)
            if not self.log_channel:
                print(f"[WARNING] Log channel with ID {self.config.channel_id} not found.")
            else:
                print(f"Logging channel set to: {self.log_channel.name}")
        else:
            print("[INFO] Logging channel ID is not set in config.yaml. Logging will be disabled.")

    # --- Member Join/Leave Events ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Logs when a member joins the server."""
        if not self.log_channel or not self.config.events.member_join_leave:
            return

        embed = embed_factory.success(
            title="メンバーが参加しました",
            description=f"{member.mention} `{member.name}`"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="アカウント作成日時", value=discord.utils.format_dt(member.created_at, style='F'))
        
        await self.log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Logs when a member leaves the server."""
        if not self.log_channel or not self.config.events.member_join_leave:
            return

        embed = embed_factory.error(
            title="メンバーが退出しました",
            description=f"{member.mention} `{member.name}`"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        
        await self.log_channel.send(embed=embed)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(LoggingCog(bot))
