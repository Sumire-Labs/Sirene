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
from .views import TicketCreateView

if TYPE_CHECKING:
    from src.main import MyBot

class TicketPanelCog(commands.Cog):
    """Commands to manage the ticket panel."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.db = self.container.db

    ticket_group = discord.SlashCommandGroup(
        "ticket",
        "チケット機能に関するコマンドです。"
    )

    @ticket_group.command(
        name="create_panel",
        description="チケット作成パネルを現在のチャンネルに設置します。"
    )
    @commands.has_permissions(manage_guild=True)
    async def create_panel(self, ctx: discord.ApplicationContext):
        
        settings = await self.db.get_guild_settings(ctx.guild.id)
        if not settings or not settings.ticket_panel_channel_id:
            await ctx.respond(embed=embed_factory.error("設定エラー", "チケットパネルを設置するチャンネルが設定されていません。\n`/config`の「チケット設定」から先に設定してください。"), ephemeral=True)
            return
        
        if ctx.channel.id != settings.ticket_panel_channel_id:
            panel_channel = self.bot.get_channel(settings.ticket_panel_channel_id)
            channel_mention = panel_channel.mention if panel_channel else "不明なチャンネル"
            await ctx.respond(embed=embed_factory.error("コマンドエラー", f"このコマンドは、設定されたチケットパネル用チャンネル ({channel_mention}) でのみ実行できます。"), ephemeral=True)
            return

        embed = embed_factory.info(
            title="サポートチケット",
            description="サーバーに関する質問や、ユーザーへの報告などはこちらからチケットを作成してください。\n下のボタンを押すと、あなた専用のプライベートチャンネルが作成されます。"
        )
        view = TicketCreateView()
        await ctx.send(embed=embed, view=view)
        await ctx.respond("チケットパネルを設置しました。", ephemeral=True)


def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(TicketPanelCog(bot))