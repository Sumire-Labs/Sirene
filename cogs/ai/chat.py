import discord
from discord.ext import commands
from typing import TYPE_CHECKING, Annotated

from . import ai_group

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.di import container
from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

class ChatCog(commands.Cog):
    """A cog for AI-powered chat commands."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.ai_service = self.container.ai_service
        self.config_loader = self.container.config_loader

    # Using a command group for better organization

    @ai_group.command(
        name="ask",
        description="AIに質問します。"
    )
    async def ask(
        self, 
        ctx: discord.ApplicationContext,
        prompt: Annotated[str, discord.Option(description="AIへの質問内容", required=True)]
    ):
        """Handles the /ai ask command."""
        # Check if the command is enabled in commands.yaml
        command_config = self.config_loader.commands.cogs["ai"].commands
        if not command_config or not command_config.get("ask", False):
            await ctx.respond(embed=embed_factory.error("Command Disabled", "This command is currently disabled by the administrator."), ephemeral=True)
            return

        # Acknowledge the command immediately and show a "thinking" state
        await ctx.defer()

        # Call the AI service from the container
        response_text = await self.ai_service.ask_question(prompt)

        # Create an embed for the response
        embed = embed_factory.info(
            title="AI Response",
            description=response_text
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Original Prompt", value=f"```\n{prompt[:1000]}\n```", inline=False)
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_footer(text="Powered by Sirene AI", icon_url=self.bot.user.display_avatar.url)
        else:
            embed.set_footer(text="Powered by Sirene AI")

        await ctx.followup.send(embed=embed)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    # Before adding the cog, check if the AI service was initialized
    if container.ai_service.initialized:
        bot.add_cog(ChatCog(bot))
    else:
        print("[WARNING] AI Cog (Chat) was not loaded because the AIService failed to initialize.")
