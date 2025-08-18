import discord
from discord.ext import commands
from discord.ui import View, Button, button, Item
import io
from typing import TYPE_CHECKING, Annotated

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.di import container
from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

# --- Action View for Image Generation ---

class ImageActionView(View):
    def __init__(self, image_cog: "ImageCog", prompt: str):
        super().__init__(timeout=300)  # 5-minute timeout
        self.image_cog = image_cog
        self.prompt = prompt
        self.message: discord.InteractionMessage | None = None

    @button(label="再生成", style=discord.ButtonStyle.primary, emoji="🔄")
    async def regenerate_callback(self, button: Button, interaction: discord.Interaction):
        """Callback for the regenerate button."""
        await interaction.response.defer()
        await self.image_cog.generate_and_respond(interaction, self.prompt, is_regenerate=True)

    @button(label="削除", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_callback(self, button: Button, interaction: discord.Interaction):
        """Callback for the delete button."""
        if interaction.message:
            await interaction.message.delete()

    async def on_timeout(self):
        """Disables all buttons when the view times out."""
        for item in self.children:
            if isinstance(item, (Button, discord.ui.Select)):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

class ImageCog(commands.Cog):
    """A cog for AI-powered image generation."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.ai_service = self.container.ai_service
        self.config_loader = self.container.config_loader

    async def generate_and_respond(self, interaction: discord.Interaction | discord.ApplicationContext, prompt: str, is_regenerate: bool = False):
        """Helper function to generate an image and respond to an interaction."""
        image_data = await self.ai_service.generate_image(prompt)

        if isinstance(image_data, str):
            error_embed = embed_factory.error("画像生成に失敗しました", image_data)
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        if not image_data:
            error_embed = embed_factory.error("画像生成に失敗しました", "AIサービスからデータが返されませんでした。")
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        image_stream = image_data[0]
        image_stream.seek(0)
        d_file = discord.File(image_stream, filename="generated_image.png")  # type: ignore
        
        author = interaction.user

        # Create a new embed with a neutral design to frame the image
        embed = embed_factory.default(
            title="",
            description=f"> {prompt[:2000]}"
        )
        if author:
            embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
        embed.set_image(url="attachment://generated_image.png")

        view = ImageActionView(self, prompt)

        if is_regenerate and isinstance(interaction, discord.Interaction):
            message = await interaction.edit_original_response(embed=embed, file=d_file, view=view)
        else:
            message = await interaction.followup.send(embed=embed, file=d_file, view=view)
        
        view.message = message

    @commands.slash_command(
        name="imagine",
        description="AIに画像生成を依頼します。"
    )
    async def imagine(
        self,
        ctx: discord.ApplicationContext,
        prompt: Annotated[str, discord.Option(description="生成したい画像の説明（プロンプト）", required=True)]
    ):
        """Handles the /imagine command."""
        command_config = self.config_loader.commands.cogs["ai"].commands
        if not command_config or not command_config.get("imagine", False):
            await ctx.respond(embed=embed_factory.error("コマンドが無効です", "このコマンドは現在、管理者によって無効化されています。 সম্প"), ephemeral=True)
            return

        await ctx.defer()
        await self.generate_and_respond(ctx, prompt, is_regenerate=False)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    if container.ai_service.initialized:
        bot.add_cog(ImageCog(bot))
    else:
        print("[WARNING] AI Cog (Image) was not loaded because the AIService failed to initialize.")