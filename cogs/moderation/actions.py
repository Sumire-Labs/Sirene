import discord
from discord.ext import commands
from typing import TYPE_CHECKING, Annotated
import datetime

# Add the project root to the Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from core.di import container
from utils.embeds import embed_factory

if TYPE_CHECKING:
    from src.main import MyBot

class ModerationActionsCog(commands.Cog):
    """A cog for basic moderation action commands."""

    def __init__(self, bot: "MyBot"):
        self.bot = bot
        self.container = self.bot.container

    async def notify_user(self, target: discord.Member, action: str, reason: str, guild_name: str):
        """Helper function to send a DM notification to the affected user."""
        try:
            embed = embed_factory.warning(
                title=f"{guild_name}からの通知",
                description=f"あなたはサーバーから **{action}** されました。"
            )
            embed.add_field(name="理由", value=reason, inline=False)
            await target.send(embed=embed)
        except discord.Forbidden:
            pass  # Cannot send DMs to this user.
        except Exception as e:
            print(f"Failed to DM user {target.id}: {e}")

    @commands.slash_command(
        name="timeout",
        description="指定したメンバーをタイムアウトさせます。"
    )
    @commands.has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: discord.ApplicationContext,
        member: Annotated[discord.Member, discord.Option(description="タイムアウトさせるメンバー", required=True)],
        duration_str: Annotated[str, discord.Option(description="期間 (例: 1h, 30m, 1d)", required=True)],
        reason: Annotated[str | None, discord.Option(description="理由（任意）", required=False)] = None
    ):
        final_reason = reason if reason is not None else "理由が指定されていません。"

        duration_map = {"m": 60, "h": 3600, "d": 86400}
        unit = duration_str[-1]
        if unit not in duration_map or not duration_str[:-1].isdigit():
            await ctx.respond(embed=embed_factory.error("無効な期間", "期間の形式が不正です。例: `30m`, `2h`, `1d`"), ephemeral=True)
            return

        seconds = int(duration_str[:-1]) * duration_map[unit]
        delta = datetime.timedelta(seconds=seconds)

        await ctx.defer()
        await self.notify_user(member, "タイムアウト", final_reason, ctx.guild.name)

        try:
            await member.timeout(until=discord.utils.utcnow() + delta, reason=final_reason)
            embed = embed_factory.success(
                title="タイムアウト成功",
                description=f"{member.mention} を **{duration_str}** タイムアウトしました。"
            )
            embed.add_field(name="理由", value=final_reason)
            await ctx.followup.send(embed=embed)
        except Exception as e:
            await ctx.followup.send(embed=embed_factory.error("エラー", f"タイムアウト処理中にエラーが発生しました: {e}"))

    @commands.slash_command(
        name="kick",
        description="指定したメンバーをサーバーからKickします。"
    )
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: discord.ApplicationContext,
        member: Annotated[discord.Member, discord.Option(description="Kickするメンバー", required=True)],
        reason: Annotated[str | None, discord.Option(description="理由（任意）", required=False)] = None
    ):
        final_reason = reason if reason is not None else "理由が指定されていません。"

        await ctx.defer()
        await self.notify_user(member, "Kick", final_reason, ctx.guild.name)

        try:
            await member.kick(reason=final_reason)
            embed = embed_factory.success(
                title="Kick成功",
                description=f"{member.mention} をサーバーからKickしました。"
            )
            embed.add_field(name="理由", value=final_reason)
            await ctx.followup.send(embed=embed)
        except Exception as e:
            await ctx.followup.send(embed=embed_factory.error("エラー", f"Kick処理中にエラーが発生しました: {e}"))

    @commands.slash_command(
        name="ban",
        description="指定したメンバーをサーバーからBANします。"
    )
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: discord.ApplicationContext,
        member: Annotated[discord.Member, discord.Option(description="BANするメンバー", required=True)],
        reason: Annotated[str | None, discord.Option(description="理由（任意）", required=False)] = None
    ):
        final_reason = reason if reason is not None else "理由が指定されていません。"

        await ctx.defer()
        await self.notify_user(member, "BAN", final_reason, ctx.guild.name)

        try:
            await member.ban(reason=final_reason)
            embed = embed_factory.success(
                title="BAN成功",
                description=f"{member.mention} をサーバーからBANしました。"
            )
            embed.add_field(name="理由", value=final_reason)
            await ctx.followup.send(embed=embed)
        except Exception as e:
            await ctx.followup.send(embed=embed_factory.error("エラー", f"BAN処理中にエラーが発生しました: {e}"))


def setup(bot: "MyBot"):
    """The setup function for the cog."""
    bot.add_cog(ModerationActionsCog(bot))