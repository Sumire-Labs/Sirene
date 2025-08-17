import discord
from datetime import datetime

# --- Color Palette (inspired by Material Design) ---
# You can customize these colors to fit your bot's personality.
SUCCESS_COLOR = 0x4CAF50  # Green
ERROR_COLOR = 0xF44336    # Red
INFO_COLOR = 0x2196F3     # Blue
WARNING_COLOR = 0xFFC107   # Amber

class Embeds:
    """A factory for creating standardized Discord embeds."""

    def __init__(self, bot_user: discord.ClientUser | None = None):
        self.bot_user = bot_user

    def set_bot_user(self, bot_user: discord.ClientUser | None):
        """Set the bot user to be used for the footer."""
        self.bot_user = bot_user

    def _create_base_embed(self, title: str, description: str, color: int) -> discord.Embed:
        """Creates a base embed with common attributes."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow()
        )
        if self.bot_user:
            embed.set_footer(text=f"Powered by {self.bot_user.name}", icon_url=self.bot_user.display_avatar.url)
        return embed

    def success(self, title: str, description: str) -> discord.Embed:
        """Creates a success embed."""
        return self._create_base_embed(f"✅ {title}", description, SUCCESS_COLOR)

    def error(self, title: str, description: str) -> discord.Embed:
        """Creates an error embed."""
        return self._create_base_embed(f"❌ {title}", description, ERROR_COLOR)

    def info(self, title: str, description: str) -> discord.Embed:
        """Creates an informational embed."""
        return self._create_base_embed(f"ℹ️ {title}", description, INFO_COLOR)

    def warning(self, title: str, description: str) -> discord.Embed:
        """Creates a warning embed."""
        return self._create_base_embed(f"⚠️ {title}", description, WARNING_COLOR)

# --- Singleton instance for easy access ---
# This instance can be imported and used across the application.
# The bot user will be set once the bot is ready.
embed_factory = Embeds()

# How to use in a cog:
# from utils.embeds import embed_factory
#
# ...
# await ctx.respond(embed=embed_factory.success("Ping!", "Pong!"))
