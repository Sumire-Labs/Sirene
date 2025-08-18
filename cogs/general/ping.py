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
        await ctx.defer()

        # Check if the command is enabled
        ping_enabled = self.container.config_loader.commands.cogs["general"].commands.get("ping", True)
        if not ping_enabled:
            await ctx.followup.send(embed=embed_factory.error("コマンドが無効です", "このコマンドは現在、管理者によって無効化されています。"), ephemeral=True)
            return

        # Get Discord API latency
        discord_latency = round(self.bot.latency * 1000)

        # Measure latencies to DB and AI services concurrently
        db_ping_task = self.container.db.ping()
        ai_ping_task = self.container.ai_service.ping()
        
        db_latency, ai_latency = await asyncio.gather(db_ping_task, ai_ping_task)

        # Format latencies
        def format_latency(value: float) -> str:
            if value < 0:
                return "`測定失敗`"
            return f"`{round(value)}ms`"

        embed = embed_factory.default(
            title="Pong! 🏓",
            description="各種サービスへの応答速度は以下の通りです。"
        )
        embed.add_field(name="🌐 Discord API", value=format_latency(discord_latency), inline=True)
        embed.add_field(name="🗃️ データベース", value=format_latency(db_latency), inline=True)
        embed.add_field(name="🧠 AI サービス", value=format_latency(ai_latency), inline=True)

        await ctx.followup.send(embed=embed)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(PingCog(bot))
