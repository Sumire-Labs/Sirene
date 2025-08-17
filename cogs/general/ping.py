import discord
from discord.ext import commands
from typing import TYPE_CHECKING

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.embeds import embed_factory

if TYPE_CHECKING:
    # This avoids circular imports. It's only for type checking.
    from src.main import MyBot

class PingCog(commands.Cog):
    """A cog for the /ping command."""

    def __init__(self, bot: "MyBot"): # Use a string forward reference for the type hint
        self.bot = bot
        # Access the container from the bot instance
        self.container = self.bot.container

    @commands.slash_command(
        name="ping",
        description="BOTの応答速度などを測定します。"
    )
    async def ping(self, ctx: discord.ApplicationContext):
        """Responds with the bot's latency."""
        # Example of checking config from the container
        ping_enabled = self.container.config_loader.commands.cogs["general"].commands.get("ping", True)
        if not ping_enabled:
            await ctx.respond(embed=embed_factory.error("Command Disabled", "This command is currently disabled."), ephemeral=True)
            return

        latency_ms = round(self.bot.latency * 1000)
        
        embed = embed_factory.info(
            title="Pong! 🏓",
            description=f"My heartbeat latency is **{latency_ms}ms**."
        )
        await ctx.respond(embed=embed)

def setup(bot: "MyBot"): # Also type hint here for consistency
    """The setup function for the cog."""
    bot.add_cog(PingCog(bot))
