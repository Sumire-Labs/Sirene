import discord
from discord.ext import commands
import io
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

class ImageCog(commands.Cog):
    """A cog for AI-powered image generation."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.ai_service = self.container.ai_service
        self.config_loader = self.container.config_loader

    # Re-using the same group from chat.py works fine as long as one is loaded.

    @ai_group.command(
        name="imagine",
        description="Generate an image from a text prompt using AI."
    )
    async def imagine(
        self,
        ctx: discord.ApplicationContext,
        prompt: Annotated[str, discord.Option(description="Describe the image you want to create.", required=True)]
    ):
        """Handles the /ai imagine command."""
        # Check if the command is enabled
        command_config = self.config_loader.commands.cogs["ai"].commands
        if not command_config or not command_config.get("imagine", False):
            await ctx.respond(embed=embed_factory.error("Command Disabled", "This command is currently disabled."), ephemeral=True)
            return

        await ctx.defer()

        # Call the AI service to get image data
        image_data = await self.ai_service.generate_image(prompt)

        if isinstance(image_data, str): # Error case
            await ctx.followup.send(embed=embed_factory.error("Image Generation Failed", image_data))
            return
        
        if not image_data:
            await ctx.followup.send(embed=embed_factory.error("Image Generation Failed", "The AI service returned no data."))
            return

        # Convert the first image's data into a discord.File
        first_image_stream = image_data[0]
        first_image_stream.seek(0) # Reset stream position
        d_file = discord.File(first_image_stream, filename="generated_image.png")

        embed = embed_factory.success(
            title="Image Generated!",
            description=f"Here is the image you requested."
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Original Prompt", value=f"```\n{prompt[:1000]}\n```", inline=False)
        embed.set_image(url="attachment://generated_image.png")

        await ctx.followup.send(embed=embed, file=d_file)


def setup(bot: "MyBot"):
    """The setup function for the cog."""
    if container.ai_service.initialized:
        bot.add_cog(ImageCog(bot))
    else:
        print("[WARNING] AI Cog (Image) was not loaded because the AIService failed to initialize.")
