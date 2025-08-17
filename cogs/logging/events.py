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

class LoggingCog(commands.Cog):
    """Handles logging of various server events."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container
        self.config = self.container.config_loader.config.logging
        self.db = self.container.db

    async def get_log_settings(self, guild_id: int) -> tuple[discord.TextChannel | None, bool]:
        """Helper to get the log channel and enabled status for a guild."""
        settings = await self.db.get_guild_settings(guild_id)

        if not settings:
            return (None, True) # Defaults: no channel, but logging is conceptually on

        if not settings.logging_enabled:
            return (None, False)

        channel = None
        if settings.log_channel_id:
            channel = self.bot.get_channel(settings.log_channel_id)
            if not isinstance(channel, discord.TextChannel):
                channel = None
        
        return channel, True

    # --- Member Join/Leave Events ---
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.config.events.member_join_leave: return
        log_channel, enabled = await self.get_log_settings(member.guild.id)
        if not enabled or not log_channel: return

        embed = embed_factory.success(
            title="メンバーが参加しました",
            description=f"{member.mention} `{member.name}`"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="アカウント作成日時", value=discord.utils.format_dt(member.created_at, style='F'))
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not self.config.events.member_join_leave: return
        log_channel, enabled = await self.get_log_settings(member.guild.id)
        if not enabled or not log_channel: return

        embed = embed_factory.error(
            title="メンバーが退出しました",
            description=f"{member.mention} `{member.name}`"
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await log_channel.send(embed=embed)

    # --- Message Events ---
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not self.config.events.message_edit_delete: return
        if not message.guild: return
        log_channel, enabled = await self.get_log_settings(message.guild.id)
        if not enabled or not log_channel: return
        if message.author.bot or message.channel == log_channel: return

        content = message.content if message.content else "（本文なし、または取得できませんでした）"
        channel_display = message.channel.mention if isinstance(message.channel, (discord.TextChannel, discord.Thread)) else f"`{message.channel}`"
        embed = embed_factory.error(
            title="メッセージが削除されました",
            description=f"**チャンネル:** {channel_display}"
        )
        embed.set_author(name=f"{message.author.name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="内容", value=f"```\n{content[:1000]}\n```", inline=False)
        if message.attachments:
            files = ", ".join([f"`{att.filename}`" for att in message.attachments])
            embed.add_field(name="添付ファイル", value=files, inline=False)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not self.config.events.message_edit_delete: return
        if not before.guild: return
        log_channel, enabled = await self.get_log_settings(before.guild.id)
        if not enabled or not log_channel: return
        if before.author.bot or before.channel == log_channel: return
        if before.content == after.content: return

        before_content = before.content if before.content else "（取得できませんでした）"
        after_content = after.content if after.content else "（取得できませんでした）"
        channel_display = before.channel.mention if isinstance(before.channel, (discord.TextChannel, discord.Thread)) else f"`{before.channel}`"
        embed = embed_factory.warning(
            title="メッセージが編集されました",
            description=f"**チャンネル:** {channel_display} [メッセージへ移動]({after.jump_url})"
        )
        embed.set_author(name=f"{before.author.name} ({before.author.id})", icon_url=before.author.display_avatar.url)
        embed.add_field(name="編集前", value=f"```\n{before_content[:1000]}\n```", inline=False)
        embed.add_field(name="編集後", value=f"```\n{after_content[:1000]}\n```", inline=False)
        await log_channel.send(embed=embed)

    # --- Role Events ---
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        if not self.config.events.role_changes: return
        log_channel, enabled = await self.get_log_settings(role.guild.id)
        if not enabled or not log_channel: return

        embed = embed_factory.success(
            title="ロールが作成されました",
            description=f"**ロール名:** `{role.name}`\n**ID:** `{role.id}`"
        )
        if role.color != discord.Color.default():
            embed.color = role.color
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if not self.config.events.role_changes: return
        log_channel, enabled = await self.get_log_settings(role.guild.id)
        if not enabled or not log_channel: return

        embed = embed_factory.error(
            title="ロールが削除されました",
            description=f"**ロール名:** `{role.name}`\n**ID:** `{role.id}`"
        )
        if role.color != discord.Color.default():
            embed.color = role.color
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if not self.config.events.role_changes: return
        log_channel, enabled = await self.get_log_settings(before.guild.id)
        if not enabled or not log_channel: return
        if before.name == after.name and before.color == after.color: return

        embed = embed_factory.warning(
            title="ロールが更新されました",
            description=f"**ロール:** {after.mention} (`{after.name}`)"
        )
        if before.name != after.name:
            embed.add_field(name="名前の変更", value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.color != after.color:
            embed.add_field(name="色の変更", value=f"`{before.color}` → `{after.color}`", inline=False)
            embed.color = after.color
        await log_channel.send(embed=embed)

def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(LoggingCog(bot))