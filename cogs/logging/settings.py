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

class LoggingSettingsCog(commands.Cog, name="LoggingSettings"):
    """Commands to configure logging for the server."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.db = self.container.db

    logging_group = discord.SlashCommandGroup(
        "logging",
        "ロギング機能に関する設定を行います。"
    )

    @logging_group.command(
        name="set_channel",
        description="このサーバーのログを投稿するチャンネルを設定します。"
    )
    @commands.has_permissions(manage_guild=True)
    async def set_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: Annotated[discord.TextChannel, discord.Option(description="ログチャンネルとして指定するチャンネル", required=True)]
    ):
        await self.db.set_log_channel(ctx.guild.id, channel.id)
        embed = embed_factory.success(
            title="ログチャンネルを設定しました",
            description=f"今後、このサーバーのログは {channel.mention} に投稿されます。"
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @logging_group.command(
        name="show_channel",
        description="現在設定されているログチャンネルを表示します。"
    )
    @commands.has_permissions(manage_guild=True)
    async def show_channel(self, ctx: discord.ApplicationContext):
        channel_id = await self.db.get_log_channel(ctx.guild.id)
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            description = f"現在のログチャンネルは {channel.mention} です。" if channel else f"設定されているチャンネル (ID: `{channel_id}`) が見つかりません。"
        else:
            description = "ログチャンネルはまだ設定されていません。"
        
        embed = embed_factory.info(
            title="ログチャンネル設定",
            description=description
        )
        await ctx.respond(embed=embed, ephemeral=True)

    @logging_group.command(
        name="clear_channel",
        description="このサーバーのログチャンネル設定を解除します。"
    )
    @commands.has_permissions(manage_guild=True)
    async def clear_channel(self, ctx: discord.ApplicationContext):
        await self.db.set_log_channel(ctx.guild.id, None)
        embed = embed_factory.success(
            title="ログチャンネルを解除しました",
            description="このサーバーでのログ機能が無効になりました。"
        )
        await ctx.respond(embed=embed, ephemeral=True)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(LoggingSettingsCog(bot))