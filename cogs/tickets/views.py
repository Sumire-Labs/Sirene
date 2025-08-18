import discord
from discord.ui import View, Button, button, Modal, InputText
from typing import TYPE_CHECKING

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

class TicketCreateModal(Modal):
    def __init__(self, bot: "MyBot"):
        super().__init__(title="新規サポートチケット作成")
        self.bot = bot
        self.db = bot.container.db
        self.ai_service = bot.container.ai_service

        self.add_item(InputText(label="件名", placeholder="例: 〇〇の不具合について", required=True, max_length=100))
        self.add_item(InputText(label="詳しい内容", placeholder="いつ、どこで、何が、どうなったか、などを詳しくご記入ください。", style=discord.InputTextStyle.paragraph, required=True))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.followup.send("エラー: サーバー情報が取得できません。", ephemeral=True)

        guild = interaction.guild
        user = interaction.user
        subject = self.children[0].value
        content = self.children[1].value

        settings = await self.db.get_guild_settings(guild.id)
        if not settings or not settings.ticket_category_id or not settings.ticket_staff_role_id:
            return await interaction.followup.send("チケット機能が正しく設定されていません。管理者に連絡してください。", ephemeral=True)

        category = self.bot.get_channel(settings.ticket_category_id)
        staff_role = guild.get_role(settings.ticket_staff_role_id)
        if not category or not isinstance(category, discord.CategoryChannel) or not staff_role:
            return await interaction.followup.send("チケット設定（カテゴリまたはロール）が無効です。管理者に連絡してください。", ephemeral=True)

        try:
            ticket_number = await self.db.get_and_increment_ticket_counter(guild.id)
            channel_name = f"ticket-{ticket_number:04d}-{subject[:20]}"
            
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            ticket_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            return await interaction.followup.send(f"チャンネル作成エラー: {e}", ephemeral=True)

        await self.db.create_ticket(ticket_channel.id, guild.id, user.id)

        initial_message_embed = embed_factory.info(f"チケット: {subject}", content)
        initial_message_embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        await ticket_channel.send(f"{user.mention} {staff_role.mention}", embed=initial_message_embed)

        await interaction.followup.send(f"チケットチャンネル {ticket_channel.mention} を作成しました。", ephemeral=True)

        await ticket_channel.trigger_typing()
        prompt = (
            f"ユーザーがサポートチケットを作成しました。件名と内容は以下の通りです。"
            f"内容を分析し、考えられる解決策や、問題を特定するために必要な追加の質問を、ユーザーに分かりやすく提案してください。\n\n"
            f"---\n件名: {subject}\n内容:\n{content}\n---"
        )
        ai_response = await self.ai_service.ask_question(prompt)
        ai_embed = embed_factory.info("AIによる一次回答", ai_response)
        if self.bot.user and self.bot.user.display_avatar:
            ai_embed.set_footer(text="この回答はAIによって生成されました。スタッフが確認し、対応を引き継ぎます。", icon_url=self.bot.user.display_avatar.url)
        else:
            ai_embed.set_footer(text="この回答はAIによって生成されました。スタッフが確認し、対応を引き継ぎます。")
        await ticket_channel.send(embed=ai_embed)

class TicketCreateView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="チケットを作成", style=discord.ButtonStyle.success, emoji="✉️", custom_id="ticket_create_button")
    async def create_ticket_callback(self, button: Button, interaction: discord.Interaction):
        bot: "MyBot" = interaction.client # type: ignore
        await interaction.response.send_modal(TicketCreateModal(bot))