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

if TYPE_CHECKING:
    from src.main import MyBot

class TicketCoreCog(commands.Cog):

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.db = self.container.db
        self.ai_service = self.container.ai_service

    async def create_ticket_channel(self, interaction: discord.Interaction):
        """The core logic to create a new ticket channel."""
        # Defer response to prevent interaction timeout
        await interaction.response.defer(ephemeral=True)

        # Ensure we have a guild and user
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            await interaction.followup.send("この操作はサーバー内でのみ実行できます。", ephemeral=True)
            return

        guild = interaction.guild
        user = interaction.user

        settings = await self.db.get_guild_settings(guild.id)
        if not settings or not settings.ticket_category_id or not settings.ticket_staff_role_id:
            await interaction.followup.send("チケット機能が正しく設定されていません。管理者に連絡してください。", ephemeral=True)
            return

        category = self.bot.get_channel(settings.ticket_category_id)
        staff_role = guild.get_role(settings.ticket_staff_role_id)

        if not category or not isinstance(category, discord.CategoryChannel) or not staff_role:
            await interaction.followup.send("チケット設定（カテゴリまたはスタッフロール）が無効です。管理者に連絡してください。", ephemeral=True)
            return

        # Define channel permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        try:
            channel_name = f"ticket-{user.name}"
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket for {user.name}. Created by Sirene."
            )
        except Exception as e:
            await interaction.followup.send(f"チャンネルの作成中にエラーが発生しました: {e}", ephemeral=True)
            return

        # Record ticket in the database
        await self.db.create_ticket(ticket_channel.id, guild.id, user.id)

        # Send a welcome message in the new channel
        welcome_embed = embed_factory.info(
            title=f"ようこそ、{user.name}さん",
            description="このチャンネルはあなたとスタッフ専用です。\nご用件をできるだけ詳しくご記入ください。\n\nAIが内容を分析し、一次回答や担当者への情報提供を補助します。"
        )
        await ticket_channel.send(f"{user.mention} {staff_role.mention}", embed=welcome_embed)

        # Notify the user that the channel has been created
        await interaction.followup.send(f"チケットチャンネル {ticket_channel.mention} を作成しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handles the first message in a ticket channel to provide an AI-powered initial response."""
        if message.author.bot or not message.guild:
            return

        ticket_data = await self.db.get_ticket_by_channel(message.channel.id)
        if not ticket_data or ticket_data[3] != "open":
            return

        ticket_user_id = ticket_data[2]
        if message.author.id != ticket_user_id:
            return

        history = await message.channel.history(limit=3).flatten()
        user_messages = [m for m in history if m.author.id == ticket_user_id]
        if len(user_messages) > 1:
            return

        await message.channel.trigger_typing()

        user_inquiry = message.content
        prompt = (
            f"ユーザーがサポートチケットで最初の問い合わせをしました。"
            f"以下の内容を分析し、考えられる解決策や、問題を特定するために必要な追加の質問を、ユーザーに分かりやすく提案してください。\n\n"
            f"---\nユーザーの問い合わせ内容:\n{user_inquiry}\n---"
        )

        ai_response = await self.ai_service.ask_question(prompt)

        embed = embed_factory.info(
            title="AIによる一次回答",
            description=ai_response
        )
        if self.bot.user and self.bot.user.display_avatar:
            embed.set_footer(text="この回答はAIによって生成されました。スタッフが確認し、対応を引き継ぎます。", icon_url=self.bot.user.display_avatar.url)
        else:
            embed.set_footer(text="この回答はAIによって生成されました。スタッフが確認し、対応を引き継ぎます。")
        
        await message.channel.send(embed=embed)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(TicketCoreCog(bot))