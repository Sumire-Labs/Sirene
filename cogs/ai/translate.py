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

class TranslateCog(commands.Cog):
    """A cog for translation commands."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.ai_service = self.container.ai_service
        self.config_loader = self.container.config_loader

    @commands.slash_command(
        name="translate",
        description="テキストを他の言語に翻訳します。"
    )
    async def translate(
        self,
        ctx: discord.ApplicationContext,
        text: Annotated[str, discord.Option(description="翻訳したいテキスト", required=True)],
        target_language: Annotated[
            str,
            discord.Option(
                description="翻訳先の言語（例: 英語、中国語）",
                required=True
            )
        ],
        source_language: Annotated[
            str | None,
            discord.Option(
                description="翻訳元の言語（任意、未指定の場合は自動検出）",
                required=False
            )
        ]
    ):
        """Translates text into another language."""
        command_config = self.config_loader.commands.cogs["ai"].commands
        if not command_config or not command_config.get("translate", True):
            await ctx.respond(embed=embed_factory.error("コマンドが無効です", "このコマンドは現在、管理者によって無効化されています。" ), ephemeral=True)
            return

        await ctx.defer()

        translated_text = await self.ai_service.translate_text(
            text=text,
            target_language=target_language,
            source_language=source_language
        )

        from_lang = source_language if source_language else "自動検出"
        embed = embed_factory.default(
            title=f"{from_lang} → {target_language} 翻訳結果",
            description=""
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="原文", value=f"```\n{text[:1000]}\n```", inline=False)
        embed.add_field(name="訳文", value=f"```\n{translated_text[:1000]}\n```", inline=False)
        
        await ctx.followup.send(embed=embed)


def setup(bot: "MyBot"):
    """The setup function for the cog."""
    if container.ai_service.initialized:
        bot.add_cog(TranslateCog(bot))
    else:
        print("[WARNING] AI Cog (Translate) was not loaded because the AIService failed to initialize.")
