import discord
from discord.ext import commands
from typing import TYPE_CHECKING
import asyncio

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

class PingCog(commands.Cog):
    """A cog for the /ping command."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container

    @commands.slash_command(
        name="ping",
        description="BOTと各種サービスへの応答速度を測定します。"
    )
    async def ping(self, ctx: discord.ApplicationContext):
        """Measures and displays the latency to Discord, the DB, and the AI service."""
        # Check if the command is enabled
        ping_enabled = self.container.config_loader.commands.cogs["general"].commands.get("ping", True)
        if not ping_enabled:
            await ctx.respond(embed=embed_factory.error("コマンドが無効です", "このコマンドは現在、管理者によって無効化されています。"), ephemeral=True)
            return

        # Acknowledge the command and show a "thinking" state
        await ctx.defer()

        # Get Discord API latency
        discord_latency = round(self.bot.latency * 1000)

        # Measure latencies to DB and AI services concurrently
        db_ping_task = self.container.db.ping()
        ai_ping_task = self.container.ai_service.ping()
        
        db_latency, ai_latency = await asyncio.gather(db_ping_task, ai_ping_task)

        # Format the results
        def format_latency(name: str, value: float) -> str:
            if value < 0:
                return f"**{name}:** `測定失敗`"
            return f"**{name}:** `{round(value)}ms`"

        description = "\n".join([
            format_latency("Discord API", discord_latency),
            format_latency("データベース", db_latency),
            format_latency("AI サービス", ai_latency),
        ])

        embed = embed_factory.info(
            title="Pong! 🏓",
            description=description
        )
        await ctx.followup.send(embed=embed)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(PingCog(bot))