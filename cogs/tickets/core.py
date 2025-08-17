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

class TicketCoreCog(commands.Cog, name="TicketCore"):
    """Core logic for ticket creation and management."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.db = self.container.db

    async def create_ticket_channel(self, interaction: discord.Interaction):
        """The core logic to create a new ticket channel."""
        await interaction.response.defer(ephemeral=True, thinking=True)

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

        await self.db.create_ticket(ticket_channel.id, guild.id, user.id)

        welcome_embed = embed_factory.info(
            title=f"ようこそ、{user.name}さん",
            description="このチャンネルはあなたとスタッフ専用です。\nご用件をできるだけ詳しくご記入ください。\n\nAIが内容を分析し、一次回答や担当者への情報提供を補助します。"
        )
        await ticket_channel.send(f"{user.mention} {staff_role.mention}", embed=welcome_embed)

        await interaction.followup.send(f"チケットチャンネル {ticket_channel.mention} を作成しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handles the first message in a ticket channel to provide an AI-powered initial response."""
        # Ignore messages from bots, or in DMs
        if message.author.bot or not message.guild:
            return

        # Check if the channel is an open ticket channel
        ticket_data = await self.db.get_ticket_by_channel(message.channel.id)
        if not ticket_data or ticket_data[3] != "open": # status is the 4th column (index 3)
            return

        # Check if the message is from the user who opened the ticket
        ticket_user_id = ticket_data[2] # user_id is the 3rd column (index 2)
        if message.author.id != ticket_user_id:
            return

        # Check if this is the very first message from the user in this channel
        # We check for 3 messages: channel creation message, bot's welcome message, and the user's first message.
        history = await message.channel.history(limit=3).flatten()
        if len(history) > 2: # If more than the initial two messages exist, it's not the first message.
            return

        # --- This is the first message, let's get an AI response ---
        await message.channel.trigger_typing()

        user_inquiry = message.content
        prompt = (
            f"ユーザーがサポートチケットで最初の問い合わせをしました。"
            f"以下の内容を分析し、考えられる解決策や、問題を特定するために必要な追加の質問を、ユーザーに分かりやすく提案してください。\n\n"
            f"---\nユーザーの問い合わせ内容:
{user_inquiry}
---"
        )

        ai_response = await self.container.ai_service.ask_question(prompt)

        embed = embed_factory.info(
            title="AIによる一次回答",
            description=ai_response
        )
        embed.set_footer(text="この回答はAIによって生成されました。スタッフが確認し、対応を引き継ぎます。", icon_url=self.bot.user.display_avatar.url)
        
        await message.channel.send(embed=embed)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(TicketCoreCog(bot))