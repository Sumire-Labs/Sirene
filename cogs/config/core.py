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
from cogs.tickets.views import TicketCreateView

if TYPE_CHECKING:
    from src.main import MyBot

# --- Modals for Configuration ---

class LoggingConfigModal(Modal):
    def __init__(self, bot: "MyBot", *args, **kwargs) -> None:
        super().__init__(title="ロギング設定", *args, **kwargs)
        self.bot = bot
        self.db = bot.container.db

        self.add_item(InputText(label="ログチャンネルID", placeholder="（空欄で変更しない）", required=False))
        self.add_item(InputText(label="ロギング全体の有効/無効", placeholder="true / false", required=False))
        self.add_item(InputText(label="レイド検知の有効/無効", placeholder="true / false", required=False))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild_id:
            return await interaction.followup.send("サーバー情報が取得できません。", ephemeral=True)

        response_parts = []
        error_parts = []

        channel_id_str = self.children[0].value
        if channel_id_str:
            try:
                channel_id = int(channel_id_str)
                channel = self.bot.get_channel(channel_id)
                if not channel or not isinstance(channel, discord.TextChannel) or not channel.guild or channel.guild.id != interaction.guild_id:
                    error_parts.append(f"無効なチャンネルIDです。")
                else:
                    await self.db.set_log_channel(interaction.guild_id, channel.id)
                    response_parts.append(f"ログチャンネルを {channel.mention} に設定しました。")
            except ValueError:
                error_parts.append("チャンネルIDは数字で入力してください。")

        logging_enabled_str = self.children[1].value
        if logging_enabled_str:
            if logging_enabled_str.lower() in ["true", "t", "yes", "y", "1"]:
                await self.db.set_logging_status(interaction.guild_id, True)
                response_parts.append(f"ロギング全体を **有効** にしました。")
            elif logging_enabled_str.lower() in ["false", "f", "no", "n", "0"]:
                await self.db.set_logging_status(interaction.guild_id, False)
                response_parts.append(f"ロギング全体を **無効** にしました。")
            else:
                error_parts.append("ロギング全体の有効/無効は true または false で入力してください。")

        raid_enabled_str = self.children[2].value
        if raid_enabled_str:
            if raid_enabled_str.lower() in ["true", "t", "yes", "y", "1"]:
                await self.db.set_raid_detection_status(interaction.guild_id, True)
                response_parts.append(f"レイド検知を **有効** にしました。")
            elif raid_enabled_str.lower() in ["false", "f", "no", "n", "0"]:
                await self.db.set_raid_detection_status(interaction.guild_id, False)
                response_parts.append(f"レイド検知を **無効** にしました。")
            else:
                error_parts.append("レイド検知の有効/無効は true または false で入力してください。")

        if error_parts:
            await interaction.followup.send(embed=embed_factory.error("設定エラー", "\n".join(error_parts)), ephemeral=True)
        elif response_parts:
            await interaction.followup.send(embed=embed_factory.success("ロギング設定を更新しました", "\n".join(response_parts)), ephemeral=True)
        else:
            await interaction.followup.send("何も変更されませんでした。", ephemeral=True)

class TicketConfigModal(Modal):
    def __init__(self, bot: "MyBot", *args, **kwargs) -> None:
        super().__init__(title="チケット設定", *args, **kwargs)
        self.bot = bot
        self.db = bot.container.db

        self.add_item(InputText(label="チケットパネル用チャンネルID", placeholder="（空欄で変更しない）", required=False))
        self.add_item(InputText(label="チケット作成先カテゴリID", placeholder="（空欄で変更しない）", required=False))
        self.add_item(InputText(label="チケット対応スタッフのロールID", placeholder="（空欄で変更しない）", required=False))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild_id:
            return await interaction.followup.send("サーバー情報が取得できません。", ephemeral=True)

        panel_id_str = self.children[0].value
        cat_id_str = self.children[1].value
        role_id_str = self.children[2].value

        current_settings = await self.db.get_guild_settings(interaction.guild_id)
        if not current_settings:
            await self.db.set_ticket_config(interaction.guild_id, None, None, None)
            current_settings = await self.db.get_guild_settings(interaction.guild_id)
            if not current_settings:
                await interaction.followup.send("データベースエラーが発生しました。", ephemeral=True)
                return

        try:
            panel_id = int(panel_id_str) if panel_id_str else current_settings.ticket_panel_channel_id
            cat_id = int(cat_id_str) if cat_id_str else current_settings.ticket_category_id
            role_id = int(role_id_str) if role_id_str else current_settings.ticket_staff_role_id

            await self.db.set_ticket_config(interaction.guild_id, panel_id, cat_id, role_id)
            embed = embed_factory.success("チケット設定を更新しました", "設定がデータベースに保存されました。")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except ValueError:
            embed = embed_factory.error("設定エラー", "IDはすべて数字で入力してください。")
            await interaction.followup.send(embed=embed, ephemeral=True)

# --- Action Views ---

class LoggingActionView(View):
    def __init__(self, bot: "MyBot"):
        super().__init__(timeout=180)
        self.bot = bot

    @button(label="設定を編集", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_config_callback(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(LoggingConfigModal(self.bot))

class TicketActionView(View):
    def __init__(self, bot: "MyBot"):
        super().__init__(timeout=180)
        self.bot = bot

    @button(label="このチャンネルにパネルを設置", style=discord.ButtonStyle.success, emoji="➕")
    async def create_panel_callback(self, button: Button, interaction: discord.Interaction):
        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("テキストチャンネルでのみ実行できます。", ephemeral=True)
        
        embed = embed_factory.default(
            title="✉️ サポートチケット",
            description="サーバーに関する質問や問題が発生した場合は、下のボタンを押してチケットを作成してください。\nあなた専用のプライベートチャンネルが作成され、スタッフが対応します。"
        )
        view = TicketCreateView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("チケットパネルを設置しました。", ephemeral=True)

    @button(label="設定を編集", style=discord.ButtonStyle.primary, emoji="✏️")
    async def edit_config_callback(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketConfigModal(self.bot))

# --- Main Selection View ---

class ConfigSelectionView(View):
    def __init__(self, bot: "MyBot"):
        super().__init__(timeout=180)
        self.bot = bot
        self.db = self.bot.container.db

    @button(label="ロギング設定", style=discord.ButtonStyle.secondary, emoji="📜")
    async def logging_button_callback(self, button: Button, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("エラー: サーバー情報が取得できません。", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        settings = await self.db.get_guild_settings(interaction.guild.id)
        if not settings:
            await self.db.set_log_channel(interaction.guild.id, None)
            settings = await self.db.get_guild_settings(interaction.guild.id)
            if not settings: return await interaction.followup.send("DBエラー", ephemeral=True)

        log_status = "✅ 有効" if settings.logging_enabled else "❌ 無効"
        raid_status = "✅ 有効" if settings.raid_detection_enabled else "❌ 無効"
        log_ch_obj = self.bot.get_channel(settings.log_channel_id) if settings.log_channel_id else None
        log_ch = log_ch_obj.mention if isinstance(log_ch_obj, discord.TextChannel) else "未設定"
        
        description = (
            f"**ステータス**\n"
            f"- `📜` 全体ロギング: {log_status}\n"
            f"- `🚨` レイド検知: {raid_status}\n\n"
            f"**設定**\n"
            f"- `📺` ログチャンネル: {log_ch}"
        )

        embed = embed_factory.default("ロギング設定", description)
        view = LoggingActionView(self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @button(label="チケット設定", style=discord.ButtonStyle.secondary, emoji="🎟️")
    async def ticket_button_callback(self, button: Button, interaction: discord.Interaction):
        if not interaction.guild:
            return await interaction.response.send_message("エラー: サーバー情報が取得できません。", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        settings = await self.db.get_guild_settings(interaction.guild.id)
        if not settings:
            await self.db.set_ticket_config(interaction.guild.id, None, None, None)
            settings = await self.db.get_guild_settings(interaction.guild.id)
            if not settings: return await interaction.followup.send("DBエラー", ephemeral=True)

        cat_ch_obj = self.bot.get_channel(settings.ticket_category_id) if settings.ticket_category_id else None
        staff_role_obj = interaction.guild.get_role(settings.ticket_staff_role_id) if settings.ticket_staff_role_id else None
        cat_ch = f"`{cat_ch_obj.name}`" if isinstance(cat_ch_obj, discord.CategoryChannel) else "未設定"
        staff_role = staff_role_obj.mention if staff_role_obj else "未設定"

        description = (
            f"- `📂` 作成先カテゴリ: {cat_ch}\n"
            f"- `👥` スタッフロール: {staff_role}"
        )

        embed = embed_factory.default("チケット設定", description)
        view = TicketActionView(self.bot)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# --- Cog with the /config command ---

class ConfigCog(commands.Cog):
    def __init__(self, bot: "MyBot"):
        self.bot = bot

    @commands.slash_command(name="config", description="BOTの各種機能設定を行います。")
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx: discord.ApplicationContext):
        embed = embed_factory.default(
            title="⚙️ BOT機能設定",
            description="設定したい機能のボタンを押してください。"
        )
        view = ConfigSelectionView(self.bot)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

def setup(bot: "MyBot"):
    bot.add_cog(ConfigCog(bot))