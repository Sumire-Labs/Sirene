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

        # Pre-fill with current settings
        # This requires an async __init__ or a helper, so we'll do it in the callback for now.
        self.add_item(InputText(label="ログチャンネルID", placeholder="ログを投稿したいチャンネルのIDを入力...", required=False))
        self.add_item(InputText(label="ロギングの有効/無効", placeholder="true または false を入力", required=False))

    async def callback(self, interaction: discord.Interaction):
        channel_id_str = self.children[0].value
        enabled_str = self.children[1].value
        
        response_parts = []
        error_parts = []

        # --- Validate and update channel ID ---
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

        # --- Validate and update enabled status ---
        if enabled_str:
            if enabled_str.lower() in ["true", "t", "yes", "y", "1"]:
                enabled = True
                await self.db.set_logging_status(self.guild_id, enabled)
                response_parts.append(f"ロギングを **有効** にしました。")
            elif enabled_str.lower() in ["false", "f", "no", "n", "0"]:
                enabled = False
                await self.db.set_logging_status(self.guild_id, enabled)
                response_parts.append(f"ロギングを **無効** にしました。")
            else:
                error_parts.append("有効/無効の値は true または false で入力してください。")

        # --- Send response ---
        if error_parts:
            embed = embed_factory.error("設定エラー", "\n".join(error_parts))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif response_parts:
            embed = embed_factory.success("ロギング設定を更新しました", "\n".join(response_parts))
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # No input was given
            await interaction.response.send_message("何も変更されませんでした。", ephemeral=True)


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

    # @button(label="チケット設定", style=discord.ButtonStyle.secondary, emoji="🎟️")
    # async def ticket_button_callback(self, button: Button, interaction: discord.Interaction):
    #     await interaction.response.send_message("チケット設定は現在開発中です。", ephemeral=True)

# --- Cog with the /config command ---

class ConfigCog(commands.Cog, name="Config"):
    """The main command to configure the bot's features."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.db = self.container.db

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
