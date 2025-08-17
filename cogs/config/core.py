import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, InputText, button
from typing import TYPE_CHECKING

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.di import container
from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

# --- Modals for configuration ---

class LoggingConfigModal(Modal):
    def __init__(self, bot: "MyBot", db, guild_id: int, *args, **kwargs) -> None:
        super().__init__(title="ロギング設定", *args, **kwargs)
        self.bot = bot
        self.db = db
        self.guild_id = guild_id

        self.add_item(InputText(label="ログチャンネルID", placeholder="ログを投稿したいチャンネルのIDを入力...", required=False))
        self.add_item(InputText(label="ロギング全体の有効/無効", placeholder="true または false を入力", required=False))
        self.add_item(InputText(label="レイド検知の有効/無効", placeholder="true または false を入力", required=False))

    async def callback(self, interaction: discord.Interaction):
        channel_id_str = self.children[0].value
        logging_enabled_str = self.children[1].value
        raid_enabled_str = self.children[2].value
        
        response_parts = []
        error_parts = []

        if channel_id_str:
            try:
                channel_id = int(channel_id_str)
                channel = self.bot.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel) or channel.guild.id != self.guild_id:
                    error_parts.append(f"無効なチャンネルIDです。このサーバーに存在するテキストチャンネルのIDを入力してください。")
                else:
                    await self.db.set_log_channel(self.guild_id, channel.id)
                    response_parts.append(f"ログチャンネルを {channel.mention} に設定しました。")
            except ValueError:
                error_parts.append("チャンネルIDは数字で入力してください。")

        if logging_enabled_str:
            if logging_enabled_str.lower() in ["true", "t", "yes", "y", "1"]:
                await self.db.set_logging_status(self.guild_id, True)
                response_parts.append(f"ロギング全体を **有効** にしました。")
            elif logging_enabled_str.lower() in ["false", "f", "no", "n", "0"]:
                await self.db.set_logging_status(self.guild_id, False)
                response_parts.append(f"ロギング全体を **無効** にしました。")
            else:
                error_parts.append("ロギング全体の有効/無効は true または false で入力してください。")

        if raid_enabled_str:
            if raid_enabled_str.lower() in ["true", "t", "yes", "y", "1"]:
                await self.db.set_raid_detection_status(self.guild_id, True)
                response_parts.append(f"レイド検知を **有効** にしました。")
            elif raid_enabled_str.lower() in ["false", "f", "no", "n", "0"]:
                await self.db.set_raid_detection_status(self.guild_id, False)
                response_parts.append(f"レイド検知を **無効** にしました。")
            else:
                error_parts.append("レイド検知の有効/無効は true または false で入力してください。")

        if error_parts:
            await interaction.response.send_message(embed=embed_factory.error("設定エラー", "\n".join(error_parts)), ephemeral=True)
        elif response_parts:
            await interaction.response.send_message(embed=embed_factory.success("ロギング設定を更新しました", "\n".join(response_parts)), ephemeral=True)
        else:
            await interaction.response.send_message("何も変更されませんでした。", ephemeral=True)


class TicketConfigModal(Modal):
    def __init__(self, bot: "MyBot", db, guild_id: int, *args, **kwargs) -> None:
        super().__init__(title="チケット設定", *args, **kwargs)
        self.bot = bot
        self.db = db
        self.guild_id = guild_id

        self.add_item(InputText(label="チケットパネルを設置するチャンネルID", required=False))
        self.add_item(InputText(label="チケットが作成されるカテゴリID", required=False))
        self.add_item(InputText(label="チケット対応スタッフのロールID", required=False))

    async def callback(self, interaction: discord.Interaction):
        # For simplicity, we'll just save the raw IDs. Validation could be more robust.
        panel_id_str = self.children[0].value
        cat_id_str = self.children[1].value
        role_id_str = self.children[2].value

        try:
            panel_id = int(panel_id_str) if panel_id_str else None
            cat_id = int(cat_id_str) if cat_id_str else None
            role_id = int(role_id_str) if role_id_str else None

            await self.db.set_ticket_config(self.guild_id, panel_id, cat_id, role_id)
            embed = embed_factory.success("チケット設定を更新しました", "設定がデータベースに保存されました。")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ValueError:
            embed = embed_factory.error("設定エラー", "IDはすべて数字で入力してください。")
            await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Views for configuration ---

class ConfigSelectionView(View):
    def __init__(self, bot: "MyBot"):
        super().__init__(timeout=180)
        self.bot = bot
        self.db = self.bot.container.db

    @button(label="ロギング設定", style=discord.ButtonStyle.secondary, emoji="📜")
    async def logging_button_callback(self, button: Button, interaction: discord.Interaction):
        modal = LoggingConfigModal(self.bot, self.db, interaction.guild.id)
        await interaction.response.send_modal(modal)

    @button(label="チケット設定", style=discord.ButtonStyle.secondary, emoji="🎟️")
    async def ticket_button_callback(self, button: Button, interaction: discord.Interaction):
        modal = TicketConfigModal(self.bot, self.db, interaction.guild.id)
        await interaction.response.send_modal(modal)

# --- Cog with the /config command ---

class ConfigCog(commands.Cog, name="Config"):
    """The main command to configure the bot's features."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot

    @commands.slash_command(
        name="config",
        description="BOTの各種機能設定を行います。"
    )
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx: discord.ApplicationContext):
        embed = embed_factory.info(
            title="BOT機能設定",
            description="設定したい機能のボタンを押してください。"
        )
        view = ConfigSelectionView(self.bot)
        await ctx.respond(embed=embed, view=view, ephemeral=True)


def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(ConfigCog(bot))