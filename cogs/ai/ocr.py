import discord
from discord.ext import commands
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

class OcrCog(commands.Cog):
    """A cog for OCR (Optical Character Recognition) commands."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.ai_service = self.container.ai_service
        self.config_loader = self.container.config_loader

    @commands.slash_command(
        name="ocr",
        description="画像からテキストを読み取ります。"
    )
    async def ocr(
        self, 
        ctx: discord.ApplicationContext,
        image: Annotated[discord.Attachment, discord.Option(description="読み取りたい画像ファイル", required=True)]
    ):
        """Reads text from an image attachment."""
        await ctx.defer()

        # Check if the command is enabled in commands.yaml
        command_config = self.config_loader.commands.cogs["ai"].commands
        if not command_config or not command_config.get("ocr", True): # Default to True if not specified
            await ctx.followup.send(embed=embed_factory.error("コマンドが無効です", "このコマンドは現在、管理者によって無効化されています。"),
                                ephemeral=True)
            return

        # Validate attachment type
        if not image.content_type or not image.content_type.startswith("image/"):
            await ctx.followup.send(embed=embed_factory.error("無効なファイル形式", "画像ファイル（PNG, JPGなど）をアップロードしてください。"),
                                ephemeral=True)
            return

        try:
            image_bytes = await image.read()
            prompt = "この画像に写っているテキストを、改行は維持しつつ、すべて正確に書き出してください。"
            
            extracted_text = await self.ai_service.generate_text_from_image(
                image_bytes=image_bytes,
                mime_type=image.content_type,
                prompt=prompt
            )

            if not extracted_text.strip():
                extracted_text = "画像からテキストを検出できませんでした。"

            embed = embed_factory.default(
                title="画像テキストの読み取り結果",
                description=f"```\n{extracted_text}\n```"
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
            embed.set_image(url=image.url)
            await ctx.followup.send(embed=embed)

        except Exception as e:
            print(f"[ERROR] OCR command failed: {e}")
            await ctx.followup.send(embed=embed_factory.error("処理中にエラーが発生しました", str(e)))


def setup(bot: "MyBot"):
    """The setup function for the cog."""
    if container.ai_service.initialized:
        bot.add_cog(OcrCog(bot))
    else:
        print("[WARNING] AI Cog (OCR) was not loaded because the AIService failed to initialize.")